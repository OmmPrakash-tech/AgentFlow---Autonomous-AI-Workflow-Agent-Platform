"""Requires Docker. Scripted planning, real LangGraph, approvals, edits and tests."""
import hashlib
import os
from pathlib import Path
import uuid
import pytest
from app.engine import Engine, initial
from app.schemas import Start, Plan, Task, ToolRequest, AgentResponse, Evaluation
from app.store import Store
from app.tools import Gateway

pytestmark=pytest.mark.skipif(os.getenv("RUN_SANDBOX_INTEGRATION")!="true",reason="Docker sandbox integration is opt-in")

class Responses:
    def __init__(self, values):
        self.values=iter(values)
    def structured(self,schema,instruction,context):
        result=next(self.values)
        assert isinstance(result,schema)
        return result,{}

def test_failed_test_debug_edit_approval_and_passing_retest(tmp_path):
    workspace=tmp_path/"sample"; workspace.mkdir()
    source="def add(a, b):\n    return a - b\n"
    fixed="def add(a, b):\n    return a + b\n"
    (workspace/"calculator.py").write_text(source)
    (workspace/"tests").mkdir()
    (workspace/"tests"/"test_calculator.py").write_text("import unittest\nfrom calculator import add\nclass TestAdd(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(2,3),5)\n")
    tools=["read_file","run_tests","modify_file"]
    def task(id,agent,allowed):return Task(id=id,agent=agent,objective="Fix failing addition test",tools=allowed,success_criteria="Demonstrate actual result")
    initial_plan=Plan(tasks=[task("initial_test","TESTER",["run_tests"])])
    replan=Plan(tasks=[task("debug","DEBUGGER",["read_file"]),task("fix","DEVELOPER",["modify_file"]),task("retest","TESTER",["run_tests"])])
    ask_test=AgentResponse(summary="Execute tests",tool_requests=[ToolRequest(name="run_tests")])
    done=AgentResponse(summary="Evidence captured",complete=True)
    yes=Evaluation(accepted=True,summary="Verified with actual tool results")
    no=Evaluation(accepted=False,summary="Test failed",retry=True)
    responses=[
        initial_plan,ask_test,done,no,replan,
        AgentResponse(summary="Inspect bug",tool_requests=[ToolRequest(name="read_file",path="calculator.py")]),done,yes,
        AgentResponse(summary="Correct addition",tool_requests=[ToolRequest(name="modify_file",path="calculator.py",content=fixed,expected_sha256=hashlib.sha256(source.encode()).hexdigest())]),done,yes,
        ask_test,done,yes,yes
    ]
    request=Start(run_id=str(uuid.uuid4()),project_id=str(uuid.uuid4()),objective="Repair addition",workspace="sample",mode="EDIT_MODE",tools=tools,
                  agents=[{"name":name,"configuration":{"available_tools":tools}} for name in ["TESTER","DEBUGGER","DEVELOPER"]])
    store=Store("sqlite:///"+str(tmp_path/"run.db")); store.create(initial(request))
    engine=Engine(store,Gateway(tmp_path),Responses(responses))
    for _ in range(5):
        engine.run(request.run_id)
        state=store.get(request.run_id)
        if state["status"]!="WAITING_APPROVAL":break
        state["pending"]["decision"]="APPROVED"
        for approval in state["approvals"]:
            if approval["id"]==state["pending"]["id"]:approval["decision"]="APPROVED"
        state["status"]="RUNNING";store.save(state)
    assert state["status"]=="COMPLETED",state["errors"]
    tests=[r for r in state["tool_results"] if r["tool"]=="run_tests"]
    assert tests[0]["output"]["exit_code"]!=0
    assert tests[-1]["output"]["exit_code"]==0
    assert state["replan_count"]==1 and len(state["approvals"])==3
    assert (workspace/"calculator.py").read_text()==fixed
