# Browser regression checks

These tests use a running frontend, API, engine and PostgreSQL. They cover real
login, four-role controls, refresh persistence, report export, and server-enforced
approval rejection. They do not mock Qwen or claim model-driven self-correction.
The history check reuses an actual completed Qwen inspection of `calculator.py`.
Approval cases use explicitly labelled deterministic pending-action fixtures.

Use an isolated database named `agentflow_verify_*`, with the application's
migrations and a copy of the recorded real run. Do not point verification at the
normal application database. Start the API and engine against that same database;
use a workspace under the repository's ignored `work/` directory. Configure a
verification administrator, change its initial password, and set local Redis
appropriately. The frontend must proxy to this verification API.

Create an ignored JSON configuration under `work/` with these keys:
`DATABASE_URL` (JDBC), `DATABASE_USERNAME`, `DATABASE_PASSWORD`,
`ENGINE_DATABASE_URL` (SQLAlchemy), `WORKSPACE_ROOT`, `ADMIN_EMAIL`, and
`ADMIN_PASSWORD`. Optional `E2E_API_URL` defaults to `http://127.0.0.1:18080/api`.
Both database URLs must point to the same local verification database on 5432.
Never commit the configuration or generated account file.

From the repository root, using installed development dependencies:

```powershell
$env:E2E_CONFIG = "$PWD/work/final-verification/environment.json"
agent-engine/.venv/Scripts/python.exe scripts/prepare-browser-e2e.py
$env:E2E_ACCOUNTS = "$PWD/work/final-verification/browser-accounts.json"
cd frontend
npx playwright test
```

The helper creates fresh test accounts, projects, and approval fixtures. Re-run it
before repeating approval tests: rejection intentionally consumes their requests.
It rejects non-verification database names and workspaces outside `work/`.

Microsoft Edge is used headlessly by default. Set `E2E_BROWSER_CHANNEL` to another
installed Playwright-supported browser channel and `E2E_BASE_URL` for another
frontend address. Credentials are entered only into the local app; browser traces
are disabled and failure screenshots remain under ignored `work/`.

Ordinary `npm test` remains the isolated API/SSE client suite. Browser integration
is opt-in and is not substituted for the deterministic CI suite.
