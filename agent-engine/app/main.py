from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hmac
import logging
import os
import threading
import time
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from .engine import Engine, initial
from .llm import OllamaProvider
from .schemas import Start, Decision
from .store import Store, TERMINAL
from .tools import Gateway

logging.basicConfig(level=logging.INFO)
secret = os.getenv("ENGINE_SECRET", "")
store = None
engine = None
pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agentflow")
slots = threading.BoundedSemaphore(4)
active = set()
active_lock = threading.RLock()

@asynccontextmanager
async def lifespan(app):
    global store, engine
    if len(secret) < 32:
        raise RuntimeError("ENGINE_SECRET must contain at least 32 characters")
    store = Store(os.getenv("ENGINE_DATABASE_URL", "sqlite:///./agentflow.db"))
    store.recover()
    engine = Engine(store, Gateway(os.getenv("WORKSPACE_ROOT","./workspaces")), OllamaProvider())
    yield
    pool.shutdown(wait=False, cancel_futures=True)

app = FastAPI(title="AgentFlow internal agent engine", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)

def authorize(x_engine_key: str = Header(default="")):
    if not secret or not hmac.compare_digest(x_engine_key, secret):
        raise HTTPException(401, "Invalid service credentials")

@app.middleware("http")
async def size_limit(request: Request, call_next):
    size = 0
    chunks = []
    async for chunk in request.stream():
        size += len(chunk)
        if size > 131072:
            return JSONResponse({"code":"REQUEST_TOO_LARGE","message":"Request exceeds 128 KiB"}, status_code=413)
        chunks.append(chunk)
    request._body = b"".join(chunks)
    return await call_next(request)

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse({"timestamp":datetime.now(timezone.utc).isoformat(),"status":exc.status_code,
                         "code":"REQUEST_REJECTED","message":exc.detail,"path":request.url.path},status_code=exc.status_code)

@app.exception_handler(Exception)
async def failure(request, exc):
    return JSONResponse({"timestamp":datetime.now(timezone.utc).isoformat(),"status":503,
                         "code":"SERVICE_UNAVAILABLE","message":"Engine operation failed","path":request.url.path},status_code=503)

def submit(run_id):
    with active_lock:
        if run_id in active:
            raise HTTPException(409,"Run already executing")
        if not slots.acquire(blocking=False):
            raise HTTPException(429,"Engine capacity reached")
        active.add(run_id)
    def worker():
        try:
            engine.run(run_id)
        finally:
            with active_lock:
                active.discard(run_id)
            slots.release()
    pool.submit(worker)

@app.get("/health")
def health():
    return {"status":"UP","service":"agent-engine"}

@app.post("/internal/agent-runs/start", dependencies=[Depends(authorize)])
def start(request: Start):
    engine.gateway.workspace(request.workspace)
    if store.get(request.run_id):
        raise HTTPException(409,"Run already exists")
    state = initial(request)
    store.create(state)
    try:
        submit(request.run_id)
    except HTTPException:
        state["status"]="FAILED"
        state["errors"].append("CAPACITY_EXHAUSTED")
        store.save(state)
        raise
    return state

def get(run_id):
    state = store.get(run_id)
    if state is None:
        raise HTTPException(404,"Run not found")
    if state["status"]=="WAITING_APPROVAL" and state["pending"]["expires_at"]<time.time():
        state["status"]="FAILED"
        state["errors"].append("APPROVAL_TIMEOUT")
        store.save(state)
    return state

@app.get("/internal/agent-runs/{run_id}/state", dependencies=[Depends(authorize)])
def state(run_id: str):
    return get(run_id)

@app.post("/internal/agent-runs/{run_id}/cancel", dependencies=[Depends(authorize)])
def cancel(run_id: str):
    get(run_id)
    return store.cancel(run_id)

@app.post("/internal/agent-runs/{run_id}/resume", dependencies=[Depends(authorize)])
def resume(run_id: str, decision: Decision):
    with active_lock:
        s = get(run_id)
        pending = s.get("pending")
        if s["status"]!="WAITING_APPROVAL" or not pending or pending["id"]!=decision.approval_id or pending["decision"]!="PENDING":
            raise HTTPException(409,"No matching pending approval")
        if run_id in active:
            raise HTTPException(409,"Run is still pausing")
        pending["decision"]="APPROVED" if decision.approved else "REJECTED"
        for a in s["approvals"]:
            if a["id"]==pending["id"]:
                a["decision"]=pending["decision"]
        s["status"]="RUNNING"
        store.save(s)
        submit(run_id)
        return s
