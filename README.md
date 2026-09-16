# AgentFlow â€” Autonomous AI Workflow & Agent Platform

A local-model orchestration platform with a Spring Boot business API, a Python LangGraph engine, and a React execution control center. Runs plan work, request confined tools, collect evidence, evaluate progress, pause for exact-action approvals, and produce Markdown reports.

**Status: working portfolio implementation; the full specification remains partial.** See [implementation status](docs/implementation-status.md) for measured results and remaining acceptance gates. Latest code verification: **47 tests passed**, all application images built, and the assembled stack passed its smoke check. A real local Qwen guided code inspection completed with an exported evidence-backed report. No model accuracy claims are made.

## Architecture

```mermaid
flowchart LR
 UI[React control center] --> API[Spring Boot / JWT / ownership]
 API --> PG[(PostgreSQL)]
 API --> REDIS[(Redis rate limiter)]
 API -->|service key| ENG[FastAPI / LangGraph]
 ENG --> PG
 ENG --> O[Local Ollama / qwen3:8b]
 ENG --> G[Tool gateway]
 G --> W[Approved workspace]
 G --> A[Exact-action approval]
 G --> S[Optional isolated test container]
```

The existing Java 25 / Spring Boot 4.1.1 starter and its package layout were preserved. Python owns model inference; Java owns authentication, registry administration, project access, and business persistence.

## Quick start

Prerequisites: Docker Desktop running, Compose, and local Ollama with `qwen3:8b`. No model is embedded in an image.

1. Copy `.env.example` to `.env`.
2. Generate independent random values for `JWT_SECRET` and `ENGINE_SECRET` (at least 32 characters). Set a strong `DATABASE_PASSWORD`.
3. Set `ENGINE_DATABASE_URL` to `postgresql+psycopg://agentflow:YOUR_URL_ENCODED_PASSWORD@postgres:5432/agentflow`.
4. Optionally set `ADMIN_EMAIL` and a 16+ character `ADMIN_PASSWORD`; the administrator must change the password at first sign-in.
5. Run `ollama pull qwen3:8b` if the model is missing.
6. Run `docker compose up --build -d`.
7. Open [localhost:3000](http://localhost:3000), register or sign in, and register the relative project path `demo`.
8. Launch a read-only objective, such as: **Inspect this repository for production readiness. Reference actual files, and distinguish unexecuted tests from failures.**

The supplied `workspaces/demo` is a small real Python repository. Mount your own workspace root using `WORKSPACE_HOST_PATH`. Never mount your home directory or a directory containing credentials.

For Ollama inside Compose, enable the `bundled-model` profile, set `OLLAMA_BASE_URL=http://ollama:11434`, and run `docker compose --profile bundled-model exec ollama ollama pull qwen3:8b`.

## What is implemented

- BCrypt password hashing, JWT authentication, token revocation, account status, forced password reset, and backend roles.
- Administrator-assisted reset-token issuance; tokens are hashed, expire, and are single-use. Email delivery is not configured.
- Project ownership and exclusive workspace registration; paginated run and audit histories.
- Agent/tool registries, user-owned guided workflows, a visual ordered-step builder, and objective-driven planning.
- Real LangGraph routing, validated Qwen responses, bounded tool/LLM calls, evaluation, two replanning attempts, and final review.
- Persistent engine state using SQLAlchemy (PostgreSQL in Compose; SQLite for local tests), plus Java business snapshots.
- Confined reading/search, dependency manifests, heuristic security evidence, Git diff inspection, controlled edits, and optional Docker-isolated Python unittest execution.
- Approval binding to the exact request and original file hash. Rejection stops the run. Edit completion requires later successful test execution.
- Live authenticated SSE snapshots, execution timelines, evidence inspection, approval controls, and Markdown report export.

## Important operating limits

- Run **one engine process / one replica**. Worker execution has two threads and four admitted runs; cross-process leases are not implemented.
- A process restart preserves waiting approvals but marks interrupted active runs failed; it never silently replays a possible mutation.
- Compose deliberately does **not** mount the Docker socket. Containerized test execution is unavailable in the default stack. The optional host-engine sandbox configuration is described in [deployment](docs/deployment.md).
- The current test runner supports Python unittest, not arbitrary Maven/npm commands. No host-shell execution is exposed to agents.
- Security scans are heuristics, not dependency vulnerability database scans.
- Workflow graphs support ordered agent steps. Arbitrary conditional/tool-node graph editing and immutable version history are not yet implemented.
- RAG/vector retrieval, automatic long-term memory retrieval, distributed workers, and advanced evaluation campaigns are deferred.

## Development and verification

Windows Java configuration used during development:

```powershell
$env:JAVA_HOME = 'C:\Users\LENOVO\.jdks\openjdk-25.0.1'
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
cd backend
.\mvnw.cmd test
```

Python:

```text
cd agent-engine
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pytest -q
```

Frontend:

```text
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Set `VITE_API_TARGET` in an ignored `frontend/.env.local` if the API uses a port other than 8080. Production uses Nginx's same-origin API proxy.

The opt-in real-model test is `agent-engine/acceptance_ollama.py` (a non-completed run exits unsuccessfully). It runs real Ollama inference and real tools against an isolated generated sample and writes its complete state under ignored `agent-engine/work/acceptance/`. Scripted providers in unit tests measure orchestration behavior, not model intelligence.

## Documentation

[Architecture](docs/architecture.md) Â· [Agents](docs/agent-architecture.md) Â· [LangGraph](docs/langgraph.md) Â· [Tools](docs/tool-system.md) Â· [Security](docs/security.md) Â· [API](docs/api.md) Â· [Deployment](docs/deployment.md) Â· [Memory](docs/memory.md) Â· [RAG roadmap](docs/rag.md) Â· [Evaluation](docs/evaluation.md)
