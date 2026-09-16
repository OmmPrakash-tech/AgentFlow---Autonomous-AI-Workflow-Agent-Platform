# Memory and persistence

Implemented short-term memory is the durable engine run snapshot: tasks, evidence, findings, events, attempts, approvals, and results. Working memory is the bounded evidence/summaries supplied to specialist calls.

Java stores durable run history and report snapshots; prior reports can be inspected by the owner through the run API and UI. The engine does not automatically retrieve historical reports into a new objective. There is no separately indexed long-term memory store.

PostgreSQL is the production persistence target. SQLite is used for standalone local engine tests and acceptance runs. Redis does not own durable state.

Before implementing automatic long-term memory, add retention rules, per-project retrieval authorization, provenance, stale-finding detection, and deletion semantics. Avoid retaining raw secrets or entire repository dumps.
