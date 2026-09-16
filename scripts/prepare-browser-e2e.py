"""Seed explicitly labelled control fixtures in an isolated AgentFlow verification DB.

Requires E2E_CONFIG pointing to an ignored JSON file; see frontend/tests/e2e/README.md.
Never invokes or mocks the model. The completed-run browser check uses existing real history.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import uuid

import httpx
import psycopg
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "agent-engine"))
from app.engine import initial
from app.schemas import Start, Task, ToolRequest
from app.store import Store
from app.tools import Gateway

config_path = Path(os.environ["E2E_CONFIG"]).resolve()
config = json.loads(config_path.read_text())
database = config["DATABASE_URL"].rsplit("/", 1)[1]
engine_url = make_url(config["ENGINE_DATABASE_URL"])
workspace_root = Path(config["WORKSPACE_ROOT"]).resolve()
if not database.startswith("agentflow_verify_") or not workspace_root.is_relative_to(root / "work") or not config_path.is_relative_to(root / "work"):
    raise SystemExit("Use an agentflow_verify_* database and a workspace under this repository's ignored work/ directory.")
if engine_url.database != database or engine_url.host not in ("localhost", "127.0.0.1") or engine_url.port not in (None, 5432):
    raise SystemExit("Engine and API settings must reference the same local verification database on port 5432.")
accounts = {"ADMIN": {"email": config["ADMIN_EMAIL"], "password": config["ADMIN_PASSWORD"]}}
api = httpx.Client(base_url=config.get("E2E_API_URL", "http://127.0.0.1:18080/api"), timeout=20)
def request(method, path, credentials=None, token=None):
    response = api.request(method, path, json=credentials,
                           headers={"Authorization": "Bearer " + token} if token else {})
    if response.status_code != 200:
        raise RuntimeError(f"Fixture setup rejected: {method} {path}: HTTP {response.status_code}")
    return response.json()

admin = request("POST", "/auth/login", accounts["ADMIN"])
if admin["user"]["forceReset"]:
    raise SystemExit("Change the verification administrator's initial password first and update E2E_CONFIG.")
admin_token = admin["accessToken"]
completed = request("GET", "/runs", token=admin_token)["content"]
recorded = next((r for r in completed if r["status"] == "COMPLETED" and r["state"].get("llm_calls", 0) > 0), None)
if not recorded:
    raise SystemExit("A recorded real-Qwen calculator inspection must exist in this isolated database; do not fabricate it.")
accounts["recordedRunId"] = recorded["id"]

for role in ("DEVELOPER", "ANALYST", "VIEWER"):
    suffix = uuid.uuid4().hex
    credentials = {"email": f"e2e-{role.lower()}-{suffix}@example.test", "password": secrets.token_urlsafe(24)}
    session = request("POST", "/auth/register", credentials)
    folder = workspace_root / suffix
    folder.mkdir(parents=True)
    (folder / "app.py").write_text("answer = 42\n", encoding="utf-8", newline="")
    project = request("POST", "/projects", {"name": "E2E " + role, "workspacePath": suffix}, session["accessToken"])
    request("PUT", "/users/" + session["user"]["id"], {"role": role, "enabled": True, "forceReset": False}, admin_token)
    accounts[role] = {**credentials, "id": session["user"]["id"], "projectId": project["id"]}

store = Store(config["ENGINE_DATABASE_URL"])
gateway = Gateway(workspace_root)
with psycopg.connect(host="127.0.0.1", dbname=database, user=config["DATABASE_USERNAME"], password=config["DATABASE_PASSWORD"]) as db:
    for label, role, tool in (("editApproval", "DEVELOPER", "modify_file"), ("testApproval", "DEVELOPER", "run_tests"), ("viewerApproval", "VIEWER", "modify_file")):
        account = accounts[role]
        workspace = db.execute("select workspace_path from projects where id=%s", (account["projectId"],)).fetchone()[0]
        agent = "DEVELOPER" if tool == "modify_file" else "TESTER"
        start = Start(run_id=str(uuid.uuid4()), project_id=account["projectId"], objective="CONTROL VERIFICATION FIXTURE: no model invoked", workspace=workspace, mode="EDIT_MODE", tools=[tool], agents=[{"name": agent, "configuration": {"available_tools": [tool]}}])
        state = initial(start)
        task = Task(id="approval_check", agent=agent, objective=start.objective, tools=[tool], success_criteria="Rejection prevents execution")
        state["plan"] = [dict(task.model_dump(), status="RUNNING", attempts=0, summary="Deterministic approval fixture")]
        source = workspace_root / workspace / "app.py"
        action = ToolRequest(name=tool)
        if tool == "modify_file":
            evidence = gateway.read(gateway.workspace(workspace), "app.py")
            action = ToolRequest(name=tool, path="app.py", content="answer = 43\n", expected_sha256=evidence["sha256"])
        proposal = gateway.proposal(state, state["plan"][0], action)
        state.update(status="WAITING_APPROVAL", pending=proposal, approvals=[proposal.copy()])
        store.create(state)
        db.execute("insert into agent_runs(id,project_id,owner_id,objective,status,mode,snapshot,created_at,updated_at,version) values(%s,%s,%s,%s,%s,%s,%s,now(),now(),0)",
                   (state["run_id"], account["projectId"], account["id"], start.objective, state["status"], state["mode"], json.dumps(state)))
        accounts[label] = {"runId": state["run_id"], "approvalId": proposal["id"], "source": str(source), "original": source.read_bytes().decode("utf-8")}

output = config_path.parent / "browser-accounts.json"
output.write_text(json.dumps(accounts, indent=2), encoding="utf-8")
print("Browser fixture file created in the ignored verification directory. Set E2E_ACCOUNTS to", output)
