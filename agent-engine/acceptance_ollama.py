"""Opt-in real Ollama acceptance run; no model response is mocked."""
import json
import os
from pathlib import Path
import uuid
from app.engine import Engine, initial
from app.llm import OllamaProvider
from app.schemas import Start
from app.store import Store
from app.tools import Gateway

root=Path("work/acceptance").resolve()
workspace=root/"sample"
workspace.mkdir(parents=True,exist_ok=True)
(workspace/"app.py").write_text('def add(a, b):\n    return a + b\n',encoding="utf-8")
(workspace/"README.md").write_text("# Calculator\nA Python utility library. No authentication or network endpoints.\n",encoding="utf-8")
tools=["list_files","read_file","inspect_project","inspect_dependencies","security_scan","search_code"]
agents=[{"name":name,"configuration":{"available_tools":tools,"max_iterations":3}} for name in ["REPOSITORY","CODE_ANALYST","SECURITY","REVIEWER","REPORTER"]]
request=Start(run_id=str(uuid.uuid4()),project_id=str(uuid.uuid4()),objective="Inspect this small Python repository for production readiness. Use at most three tasks: inspect actual files, analyze code and security evidence, review and report. Do not run tests or edit files. Explicitly state missing tests and avoid inventing vulnerabilities.",workspace="sample",agents=agents,tools=tools)
store=Store("sqlite:///"+str(root/"acceptance.db"))
store.create(initial(request))
print("Run:",request.run_id,flush=True)
Engine(store,Gateway(root),OllamaProvider()).run(request.run_id)
result=store.get(request.run_id)
(root/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({k:result.get(k) for k in ["status","llm_calls","tool_call_count","retry_count","errors","verification"]},indent=2),flush=True)

raise SystemExit(0 if result["status"] == "COMPLETED" else 1)
