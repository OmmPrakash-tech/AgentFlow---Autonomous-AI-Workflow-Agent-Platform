# API contract

Public routes are under Spring Boot `/api`. Except registration, login, forgot/reset password, all require `Authorization: Bearer <JWT>`. IDs are UUIDs. Paged collections accept zero-based `page`, return up to 25 rows, and sort newest first.

| Method | Route | Purpose |
|---|---|---|
| POST | /auth/register, /auth/login | email + password; returns accessToken, expiresIn, safe user DTO |
| GET | /auth/me | Current safe profile |
| POST | /auth/logout | Revoke sessions |
| POST | /auth/password | currentPassword, newPassword |
| POST | /auth/forgot-password | Record administrator-assisted request |
| POST | /auth/reset-password | token + password |
| GET / PUT | /users, /users/{id} | Administrator account management |
| POST | /users/{id}/reset-token | Administrator one-time reset token |
| GET / POST | /projects | List/register relative workspaces |
| GET / POST | /agents, /tools, /workflows | Read/save validated definitions |
| GET / POST | /runs | List/start execution |
| GET | /approvals | Paginated runs waiting for approval, scoped to current user |
| GET | /runs/{id} | Latest accessible execution snapshot |
| POST | /runs/{id}/cancel | Request cancellation |
| POST | /runs/{id}/approval | approvalId + approved boolean |
| GET | /runs/{id}/events | Finite SSE state event; authenticated clients reconnect |
| GET | /runs/{id}/report | Markdown export |
| GET | /audit | Administrator audit history |

Start input:

```json
{"projectId":"UUID","objective":"Inspect this repository","mode":"READ_ONLY","workflowId":null}
```

A registry save contains `name`, `configuration`, and `enabled`. Guided workflow configuration contains `agents`, an ordered list of 1–12 enabled agent names. Saving increments the current revision; immutable historical revisions are not stored.

## Internal API

Requires `X-Engine-Key`; the service key must have 32+ characters.

| Method | Route |
|---|---|
| POST | /internal/agent-runs/start |
| GET | /internal/agent-runs/{id}/state |
| POST | /internal/agent-runs/{id}/resume |
| POST | /internal/agent-runs/{id}/cancel |

Start payload uses snake_case: run_id, project_id, objective, workspace, mode, agents, tools, and optional workflow. Java supplies the trusted registry snapshot. Resume input is `{"approval_id":"ID","approved":true}`; authorization is checked by Java and exact pending-request matching by Python.

The engine returns its persisted JSON state. The API retains the latest durable snapshot if synchronization fails; this is not a claim that the engine is still healthy.

Errors include timestamp, status, code, message and path, without stack traces. Missing dependencies fail operations safely. A source-maintained machine-readable contract is in [openapi.json](openapi.json).
