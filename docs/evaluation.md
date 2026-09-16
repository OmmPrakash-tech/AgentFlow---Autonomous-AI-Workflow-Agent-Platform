# Evaluation

Unit tests use scripted providers to measure orchestration correctness, not Qwen accuracy. They cover actual LangGraph transitions and real temporary file operations. The opt-in Ollama acceptance script performs real local inference and persists its measured results.

Available observations: task statuses, actual tool calls and results, invalid calls, retry/replan counts, approval decisions, model-call counts, and model-reported token/duration metadata when returned. No synthetic token usage is generated.

An accepted specialist task must pass evaluation and avoid failed tool results. Repository/security/code/test specialists have deterministic minimum-evidence gates. Security/code review may reuse successful inspection evidence actually included in its context; a repository task must gather its own required evidence and a test specialist must actually execute tests. The specialist's completion flag can end its loop early, but an independent evaluator can accept sufficient observed work at the iteration limit. A summary without relevant evidence cannot pass. Final review rejects failed tasks and unverified edits.

Planned evaluation campaigns should measure:
- Task completion against fixture-specific assertions.
- Tool validity and successful-tool ratio.
- Test execution outcomes (not inferred test pass percentages).
- Human interventions and rejected approvals.
- Duration and completeness of evidence-backed reports.
- Resistance to hostile README instructions and workspace escape requests.

There is no comparative model benchmark or statistical accuracy score. See implementation status for exact test and live-run results.
