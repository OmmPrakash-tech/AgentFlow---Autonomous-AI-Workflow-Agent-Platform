# Deployment and local development

## Docker Compose
The stack defines frontend, API, agent engine, PostgreSQL, Redis, and an optional Ollama service. PostgreSQL and model data use persistent volumes. Frontend and API bind only to localhost; internal data services are not published.

Set secrets in ignored .env, never source files. Database passwords containing URL-special characters must be URL-encoded inside ENGINE_DATABASE_URL. The Java JDBC password variable uses the raw value.

The default engine contacts existing host Ollama via host.docker.internal. On Linux, the host-gateway mapping is included. If the Ollama server only listens on loopback and containers cannot reach it, use the optional bundled-model service or explicitly configure the host Ollama listener according to your local network policy.

```text
docker compose config --quiet
docker compose up --build -d
docker compose logs --tail=100 api agent-engine
docker compose down
```

Do not add `--volumes` unless deliberately deleting durable data.

## Optional test runner
Default Compose does not mount the Docker socket; arbitrary repository code cannot execute in the engine container. To enable the implemented Python unittest adapter, run the engine as a dedicated local account with Docker CLI access, set `SANDBOX_ENABLED=true`, and pre-pull the trusted `python:3.14-slim` image. Keep the internal endpoint on loopback and configure Java's service URL accordingly.

Docker CLI access is privileged. This host-engine option is for trusted local workspaces. Production should use a separate narrowly scoped sandbox-runner service instead of exposing Docker to the agent-engine container.

Tests execute in a copied allowlisted snapshot with network disabled and resource limits. JVM/npm runners are not implemented. If no sandbox is available, the tool returns a controlled failure and no test success is claimed.

## Development
Use the existing Maven wrapper and Java 25. Python 3.14 and Node 24 were available on the inspected machine. Resolved Python dependencies are in requirements.lock and frontend dependencies in package-lock.json. No global runtime upgrade was performed.

Tests use H2 only through test resources. `spring-boot:test-run` can launch a temporary API smoke environment with H2; it is not a supported production database. Pass a different server port if 8080 is occupied. Engine tests use temporary SQLite files. Production Compose uses PostgreSQL.

## Readiness limits
Engine health currently confirms the HTTP process; model failures surface during runs. Java Actuator includes dependency health. Redis rate-limit failures reject affected actions instead of silently permitting them. There is no automatic failover.

For production: TLS termination, secret rotation, backups/restore drills, authenticated operator metrics, image digest pinning, network policies, distributed leases, and explicit workspace retention are still required.
