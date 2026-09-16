import json
import logging
import time
from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END
from .schemas import Plan, Task, AgentResponse, Evaluation, ToolRequest
from .store import TERMINAL
from .tools import PolicyError, redact

log = logging.getLogger("agentflow.engine")
MAX_CALLS, MAX_RETRIES, MAX_SECONDS = 36, 2, 1800

class Engine:
    def __init__(self, store, gateway, provider):
        self.store, self.gateway, self.provider = store, gateway, provider
        graph = StateGraph(dict)
        for name in ("plan", "act", "evaluate", "replan", "verify", "finalize"):
            graph.add_node(name, getattr(self, name))
        graph.add_conditional_edges(START, lambda s: "act" if s.get("plan") else "plan")
        graph.add_edge("plan", "act")
        graph.add_conditional_edges("act", lambda s: END if s["status"] == "WAITING_APPROVAL" else "evaluate")
        graph.add_conditional_edges("evaluate", lambda s: "replan" if s.get("needs_replan") else ("act" if s["cursor"] < len(s["plan"]) else "verify"))
        graph.add_edge("replan", "act")
        graph.add_edge("verify", "finalize")
        graph.add_edge("finalize", END)
        self.graph = graph.compile()

    def event(self, s, kind, detail):
        s["events"].append({"id": len(s["events"])+1, "type": kind, "time": time.time(), "detail": redact(detail)[:1000]})
        task = s["plan"][s["cursor"]] if s.get("plan") and s["cursor"] < len(s["plan"]) else {}
        log.info(json.dumps({"timestamp":time.time(),"service":"agent-engine","run_id":s["run_id"],
                             "task_id":task.get("id"),"agent":task.get("agent"),"event":kind,"status":s["status"]}))
        self.store.save(s)

    def guard(self, s):
        latest = self.store.get(s["run_id"])
        if latest["status"] == "CANCELLED":
            raise PolicyError("CANCELLED")
        if time.time()-s["started_at"] > MAX_SECONDS:
            raise PolicyError("RUN_TIMEOUT")
        if s["tool_call_count"] >= MAX_CALLS:
            raise PolicyError("TOOL_BUDGET_EXHAUSTED")
        if s["llm_calls"] >= 80:
            raise PolicyError("LLM_BUDGET_EXHAUSTED")

    def llm(self, s, schema, instruction, context):
        self.guard(s)
        for attempt in range(2):
            s["llm_calls"] += 1
            self.event(s, "LLM_REQUESTED", schema.__name__)
            try:
                value, usage = self.provider.structured(schema, instruction, context)
                s["usage"].append(usage)
                self.event(s, "LLM_COMPLETED", schema.__name__)
                return value
            except Exception as e:
                s["errors"].append("LLM_"+type(e).__name__)
                self.event(s, "LLM_FAILED", type(e).__name__)
                if attempt:
                    raise
                s["retry_count"] += 1
                feedback = str(e)[:1800] if isinstance(e, ValidationError) else type(e).__name__
                context = {**context, "validation_feedback": "Correct the previous response: " + feedback}
        raise RuntimeError("unreachable")

    def validate_plan(self, s, plan):
        agents = {a["name"]: a for a in s["agents"]}
        for t in plan.tasks:
            if t.agent not in agents or not set(t.tools) <= set(s["tools"]) or not set(t.tools) <= set(agents[t.agent]["configuration"].get("available_tools", [])):
                raise PolicyError("INVALID_PLAN_PERMISSIONS")
            if s["mode"] == "READ_ONLY" and "modify_file" in t.tools:
                raise PolicyError("READ_ONLY_PLAN")
        return [dict(t.model_dump(), status="PENDING", attempts=0, summary="") for t in plan.tasks]

    def plan(self, s):
        s["status"] = "PLANNING"
        self.event(s, "PLANNING_STARTED", s["objective"])
        if s.get("workflow"):
            names = s["workflow"].get("agents", [])
            if not names or len(names) > 12:
                raise PolicyError("INVALID_WORKFLOW")
            by_name = {a["name"]: a for a in s["agents"]}
            tasks = []
            for index, name in enumerate(names):
                if name not in by_name:
                    raise PolicyError("WORKFLOW_AGENT_DISABLED")
                tools = [t for t in by_name[name]["configuration"].get("available_tools", []) if t in s["tools"]]
                if s["mode"] == "READ_ONLY":
                    tools = [t for t in tools if t != "modify_file"]
                tasks.append(Task(id=f"guided_{index}", objective=f"{name}: {s['objective']}"[:1000], agent=name,
                    dependencies=[f"guided_{index-1}"] if index else [], tools=tools,
                    success_criteria="Provide evidence-backed specialist conclusions for the objective", priority=index+1))
            s["plan"] = self.validate_plan(s, Plan(tasks=tasks))
            self.event(s, "PLAN_CREATED", f"Guided workflow: {len(tasks)} tasks")
            return s
        plan = self.llm(s, Plan,
            "Decompose the objective into 3-6 ordered tasks. Each task selects only permitted tools from its agent. "
            "Inspect repository, gather targeted code/security/dependency evidence, then review and report. "
            "No edits in READ_ONLY. Do not request tests unless the objective requires executing them. "
            "Honor the guided workflow agent order if supplied.",
            {"objective":s["objective"], "mode":s["mode"], "agents":s["agents"], "enabled_tools":s["tools"], "workflow":s.get("workflow")})
        s["plan"] = self.validate_plan(s, plan)
        self.event(s, "PLAN_CREATED", f"{len(s['plan'])} tasks")
        return s

    def context(self, s, task):
        return {"objective":s["objective"], "task":task, "mode":s["mode"],
                "UNTRUSTED_evidence":s["tool_results"][-8:], "UNTRUSTED_findings":s["findings"][-8:],
                "previous_summaries":[t["summary"] for t in s["plan"] if t["status"]=="COMPLETED"],
                "failures":s["errors"][-5:]}

    def execute(self, s, task, request, approval=None):
        self.guard(s)
        if request.name == "list_files" and any(r["tool"] == "list_files" and r["task_id"] == task["id"] and r["status"] == "SUCCEEDED" for r in s["tool_results"]):
            self.event(s, "EVIDENCE_REUSED", "Existing workspace inventory")
            return
        s["tool_call_count"] += 1
        self.event(s, "TOOL_REQUESTED", request.name)
        try:
            result = self.gateway.execute(s, task, request, approval)
            if result["output"].get("exit_code", 0) != 0:
                result["status"] = "FAILED"
            s["tool_results"].append(result)
            self.event(s, "TOOL_"+result["status"], request.name)
        except Exception as e:
            result = {"id":str(s["tool_call_count"]), "tool":request.name,"task_id":task["id"],"status":"FAILED","output":{"error":redact(str(e))[:300]}}
            s["tool_results"].append(result)
            s["errors"].append(request.name+": "+redact(str(e))[:300])
            self.event(s, "TOOL_FAILED", request.name)

    def act(self, s):
        self.guard(s)
        s["status"] = "RUNNING"
        task = s["plan"][s["cursor"]]
        task["status"] = "RUNNING"
        self.event(s, "AGENT_STARTED", task["agent"]+": "+task["objective"])
        if not s["tool_results"] and "list_files" in task["tools"]:
            # Ground file-name choices before the small local model requests reads.
            self.execute(s, task, ToolRequest(name="list_files"))
        pending = s.get("pending")
        if pending:
            if pending["decision"] == "PENDING":
                s["status"] = "WAITING_APPROVAL"
                return s
            if pending["decision"] == "APPROVED":
                # Persist consumption before mutation. Restart recovery never replays it.
                pending["consumed"] = True
                self.store.save(s)
                self.execute(s, task, ToolRequest.model_validate(pending["request"]), pending)
            else:
                s["errors"].append("APPROVAL_REJECTED")
                task["summary"] = "Requested action was rejected by a human."
                task["status"] = "FAILED"
                s["pending"] = None
                self.event(s, "APPROVAL_REJECTED", task["id"])
                raise PolicyError("APPROVAL_REJECTED")
            s["pending"] = None
        agent = next(a for a in s["agents"] if a["name"] == task["agent"])
        limit = min(4, max(1,int(agent["configuration"].get("max_iterations",4))))
        for _ in range(limit):
            task["attempts"] += 1
            response = self.llm(s, AgentResponse,
                f"You are {task['agent']}. {agent['configuration'].get('system_instructions', '')[:4000]} Use only the task's listed tools. Request evidence first; then complete with an evidence-backed summary. "
                "Use read_file before modify_file and copy its sha256 into expected_sha256. "
                "Populate tool_requests with the tools you need: you are responsible for requesting execution, not the user. "
                "Work only on this task, not later tasks. If its success criteria are already supported by supplied evidence, stop requesting tools. "
                "Do not ask the user to provide tool evidence. Do not repeat identical tool calls. "
                "After sufficient evidence return tool_requests=[] and complete=true. complete=true means the task's success criteria have been met.",
                self.context(s, task))
            task["summary"] = response.summary
            evidence = {r["id"]:r for r in s["tool_results"] if r["status"]=="SUCCEEDED"}
            for finding in response.findings:
                source = evidence.get(finding.evidence_id)
                if source and finding.affected_file and finding.affected_file in json.dumps(source["output"]):
                    s["findings"].append(finding.model_dump())
                else:
                    s["errors"].append("UNSUPPORTED_FINDING_REJECTED")
            for request in response.tool_requests:
                if request.name in {"modify_file","run_tests"}:
                    proposal = self.gateway.proposal(s, task, request)
                    s["pending"] = proposal
                    s["approvals"].append(proposal)
                    s["status"] = "WAITING_APPROVAL"
                    self.event(s, "APPROVAL_REQUESTED", request.name)
                    return s
                self.execute(s, task, request)
            if response.complete and not response.tool_requests:
                task["status"] = "AWAITING_EVALUATION"
                break
        return s

    def evaluate(self, s):
        task = s["plan"][s["cursor"]]
        evaluation = self.llm(s, Evaluation,
            "Evaluate task success against actual evidence. Reject invented actions and failed tests. "
            "A failed tool call or unmet success criteria may require replanning. Give a concise evidence summary.",
            self.context(s, task))
        relevant = [r for r in s["tool_results"] if r["task_id"] == task["id"]]
        failed_tests = any(r["tool"]=="run_tests" and r["status"]=="FAILED" for r in relevant)
        failed_tools = any(r["status"] == "FAILED" for r in relevant)
        accepted = evaluation.accepted and not failed_tests and not failed_tools
        if task["agent"] in {"REPOSITORY", "SECURITY", "CODE_ANALYST", "TESTER"} and not relevant:
            accepted = False
        observed = {r["tool"] for r in relevant if r["status"] == "SUCCEEDED"}
        if task["agent"] == "REPOSITORY" and "read_file" in task["tools"] and "read_file" not in observed:
            accepted = False
        if task["agent"] in {"SECURITY", "CODE_ANALYST"} and not observed.intersection({"read_file", "security_scan", "search_code", "inspect_dependencies"}):
            accepted = False
        if task["agent"] == "TESTER" and "run_tests" not in observed:
            accepted = False
        if task["agent"] in {"REVIEWER", "REPORTER"} and not s["tool_results"]:
            accepted = False
        task["status"] = "COMPLETED" if accepted else "FAILED"
        task["evaluation"] = evaluation.summary
        s["needs_replan"] = not accepted and s["replan_count"] < MAX_RETRIES
        self.event(s, "TASK_"+task["status"], task["id"])
        if not s["needs_replan"]:
            s["cursor"] += 1
        return s

    def replan(self, s):
        s["replan_count"] += 1
        s["retry_count"] += 1
        self.event(s, "REPLAN_STARTED", f"Attempt {s['replan_count']}")
        remaining = self.llm(s, Plan,
            "Produce a replacement plan for the unresolved work using the failure evidence. "
            "For failed tests: investigate with DEBUGGER, propose a minimal fix with DEVELOPER only in EDIT_MODE, "
            "then TESTER and REVIEWER. Use new task IDs. Do not repeat failed approaches. Remain within permissions.",
            # Replacement tasks form their own topologically ordered DAG.
            {"objective":s["objective"],"mode":s["mode"],"agents":s["agents"],"enabled_tools":s["tools"],
             "dependency_rule":"Dependencies must refer only to earlier tasks in your returned replacement plan, never to old plan IDs.",
             "UNTRUSTED_evidence":s["tool_results"][-6:],"previous_tasks":s["plan"][s["cursor"]:]})
        replacements = self.validate_plan(s, remaining)
        s["task_history"].extend(s["plan"][s["cursor"]:])
        s["plan"] = s["plan"][:s["cursor"]] + replacements
        s["needs_replan"] = False
        return s

    def verify(self, s):
        s["status"] = "VERIFYING"
        self.event(s, "VERIFICATION_STARTED", "Reviewing measured results")
        evaluation = self.llm(s, Evaluation,
            "Perform final independent review. Accept only when the objective is supported by tool evidence. "
            "List unresolved issues; do not claim tests ran unless run_tests output exists.",
            {"objective":s["objective"],"tasks":s["plan"],"UNTRUSTED_evidence":s["tool_results"][-8:],"errors":s["errors"]})
        edits = [r for r in s["tool_results"] if r["tool"]=="modify_file" and r["status"]=="SUCCEEDED"]
        tests = [r for r in s["tool_results"] if r["tool"]=="run_tests" and r["status"]=="SUCCEEDED"]
        verified_edits = not edits or (tests and s["tool_results"].index(tests[-1]) > s["tool_results"].index(edits[-1]))
        s["verification"] = {"accepted": bool(evaluation.accepted and verified_edits and all(t["status"]=="COMPLETED" for t in s["plan"]) and s["tool_results"]),
                             "summary":evaluation.summary, "edits_verified":bool(verified_edits)}
        return s

    def finalize(self, s):
        s["status"] = "COMPLETED" if s["verification"]["accepted"] else "FAILED"
        s["completed_at"] = time.time()
        lines = ["# AgentFlow report", "", "## Objective", s["objective"], "", "## Final status", s["status"],
                 "", "## Review", s["verification"]["summary"], "", "## Tasks"]
        lines += [f"- {t['agent']} / {t['id']} — {t['status']}: {t['summary']}" for t in s["plan"]]
        lines += ["", "## Findings"] + [f"- [{f['severity']}] {f['title']} ({f['affected_file']}, evidence {f['evidence_id']}): {f['recommendation']}" for f in s["findings"]]
        lines += ["", "## Evidence"] + [f"- {r['id']}: {r['tool']} — {r['status']}" for r in s["tool_results"]]
        lines += ["", "## Tests", "See run_tests evidence." if any(r["tool"]=="run_tests" for r in s["tool_results"]) else "Tests were not executed.",
                  "", "## Execution",f"LLM calls: {s['llm_calls']}; tool calls: {s['tool_call_count']}; retries: {s['retry_count']}; replans: {s['replan_count']}; approvals: {len(s['approvals'])}",
                  "", "## Unresolved issues"] + [f"- {e}" for e in s["errors"]]
        s["report"] = "\n".join(lines)
        self.event(s, "RUN_"+s["status"], s["verification"]["summary"])
        return s

    def run(self, run_id):
        s = self.store.get(run_id)
        try:
            self.graph.invoke(s, {"recursion_limit":150})
        except Exception as e:
            latest = self.store.get(run_id)
            if latest["status"] == "CANCELLED":
                return
            latest["status"] = "FAILED"
            latest["errors"].append(type(e).__name__+": "+redact(str(e))[:300])
            latest["verification"] = {"accepted":False,"summary":"Execution stopped: "+type(e).__name__,"edits_verified":False}
            self.finalize(latest)

def initial(request):
    return {**request.model_dump(), "status":"QUEUED","plan":[],"cursor":0,"findings":[],"tool_results":[],
            "events":[],"errors":[],"approvals":[],"pending":None,"llm_calls":0,"tool_call_count":0,
            "retry_count":0,"replan_count":0,"usage":[],"task_history":[],"started_at":time.time()}
