# Agent architecture

The default registry includes PLANNER, RESEARCH, REPOSITORY, CODE_ANALYST, SECURITY, DEVELOPER, TESTER, DEBUGGER, REVIEWER, and REPORTER. Specialists share a structured response contract and receive their role, objective, permitted tools, prior summaries, and bounded evidence. Administrators can register additional named specialists and instructions.

Planner output is a validated task DAG with IDs, objectives, dependencies, tools, success criteria, priorities, and registry-checked agent names. Dependencies must refer to earlier tasks. Execution is currently sequential in topological order.

Guided workflows explicitly specify agent order; the engine creates dependent tasks from that saved order without allowing a model to reorder it. Autonomous mode uses the model to decompose the objective.

Repository inspection is grounded before model analysis: when the task permits it, the engine obtains a filtered inventory and reads at most two files through the audited gateway, preferring paths named in the objective and otherwise shallow files. These are deterministic orchestration calls, not claimed model-selected calls. The model then requests additional evidence as needed.

Only implemented tools can be selected. A custom specialist cannot add a new executable. RESEARCH currently inspects local documentation; approved external-document search is not implemented. All inference uses the deployment's qwen3:8b provider; per-agent provider/model routing remains future work.

A specialist response contains a concise summary, tool requests, evidence-linked findings, and an explicit completion flag. Completion requires independent evaluation and deterministic minimum-evidence gates. Evaluators may reject work, and a final review can fail the overall run. Findings with unknown evidence IDs or unreferenced file paths are discarded.

Developer changes pause for human approval. The gateway checks the approved content digest and original file hash. A completed edit run must have a later successful test tool result. A failed test can route through replanning to DEBUGGER, DEVELOPER, TESTER, and REVIEWER, within a maximum of two replans.
