import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app import main
from app.engine import initial, Engine
from app.schemas import Start, Decision, ToolRequest
from app.store import Store
from app.tools import Gateway

@pytest.fixture
def api_client(tmp_path, monkeypatch):
    (tmp_path/"sample").mkdir()
    (tmp_path/"sample"/"app.py").write_text("value = 1\n")
    store=Store("sqlite:///"+str(tmp_path/"api.db"))
    monkeypatch.setattr(main,"secret","test-service-key-01234567890123456789")
    monkeypatch.setattr(main,"store",store)
    monkeypatch.setattr(main,"engine",Engine(store,Gateway(tmp_path),None))
    monkeypatch.setattr(main,"submit",lambda run_id:None)
    return TestClient(main.app),store,{"X-Engine-Key":main.secret}

def body():
    return {"run_id":str(uuid.uuid4()),"project_id":str(uuid.uuid4()),"objective":"Inspect","workspace":"sample","agents":[],"tools":[]}

def test_service_auth_schema_and_body_limit(api_client):
    client,_,headers=api_client
    assert client.post("/internal/agent-runs/start",json=body()).status_code==401
    invalid=client.post("/internal/agent-runs/start",headers=headers,json={})
    assert invalid.status_code==422 and invalid.json()["code"]=="INVALID_INPUT"
    huge=client.post("/internal/agent-runs/start",headers=headers,content="x"*131073)
    assert huge.status_code==413

def test_start_persists_and_duplicate_is_rejected(api_client):
    client,store,headers=api_client
    request=body()
    response=client.post("/internal/agent-runs/start",headers=headers,json=request)
    assert response.status_code==200
    assert store.get(request["run_id"])["status"]=="QUEUED"
    assert client.post("/internal/agent-runs/start",headers=headers,json=request).status_code==409

def test_cancel_and_approval_bypass(api_client):
    client,store,headers=api_client
    request=body()
    client.post("/internal/agent-runs/start",headers=headers,json=request)
    run_id=request["run_id"]
    assert client.post(f"/internal/agent-runs/{run_id}/resume",headers=headers,json={"approval_id":"invented","approved":True}).status_code==409
    assert client.post(f"/internal/agent-runs/{run_id}/cancel",headers=headers,json={}).json()["status"]=="CANCELLED"

def test_approval_timeout_and_single_decision(api_client):
    client,store,headers=api_client
    state=initial(Start(**body())); state["status"]="WAITING_APPROVAL"
    state["pending"]={"id":"approval-1","decision":"PENDING","expires_at":time.time()+100}
    state["approvals"]=[state["pending"].copy()]
    store.create(state)
    url=f"/internal/agent-runs/{state['run_id']}/resume"
    data={"approval_id":"approval-1","approved":False}
    assert client.post(url,headers=headers,json=data).status_code==200
    assert client.post(url,headers=headers,json=data).status_code==409
    state["pending"]["expires_at"]=time.time()-1
    state["status"]="WAITING_APPROVAL"; store.save(state)
    response=client.get(f"/internal/agent-runs/{state['run_id']}/state",headers=headers)
    assert response.json()["status"]=="FAILED"
    assert "APPROVAL_TIMEOUT" in response.json()["errors"]
