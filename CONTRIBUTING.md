# Contributing to AgentFlow

Preserve the Spring Boot / FastAPI / LangGraph / Ollama boundaries. Open a focused
change describing the user-visible problem, its cause, and how the fix was verified.
Do not represent roadmap features or scripted-model tests as verified AI capability.

Use Java 25, Python 3.14, Node 24, and the checked-in dependency locks. See
[deployment](docs/deployment.md) for local settings. Keep credentials, databases,
generated files and models out of commits.

Run relevant checks from their service directories:

- Backend: `mvnw.cmd test` on Windows or `bash mvnw test` on Linux.
- Engine: `.venv/Scripts/python.exe -m pytest -q` on Windows, or the corresponding
  virtual-environment Python on Linux.
- Frontend: `npm ci`, `npm test`, `npm run build`.
- Browser regressions: [setup and commands](frontend/tests/e2e/README.md).

Real Redis verification uses `-Drun.redis.integration=true` with Redis on localhost
6379. The sandbox regression requires Docker, a pulled `python:3.14-slim` image,
and `RUN_SANDBOX_INTEGRATION=true` / `SANDBOX_ENABLED=true`. These execute real
services; report unavailable prerequisites explicitly. Never bypass isolation.

Use disposable verification databases for integration work. Preserve meaningful
existing tests, add regressions for reproduced defects, and distinguish scripted
orchestration checks from actual model runs. The opt-in Ollama acceptance harness
requires local `qwen3:8b`; it is not required for every ordinary CI run.

Review your diff for secrets and unrelated files. Keep commits meaningful and
small enough to review. Follow the repository owner's instructions before pushing.
