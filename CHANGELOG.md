# Changelog

## Unreleased

- Preserve pending approval decisions when worker admission is rejected.
- Redact quoted secrets, bearer tokens and credential-bearing URLs in tool output.
- Enforce case-insensitive sensitive-path exclusions and keep empty Git diff
  allowlists from expanding to excluded files.
- Avoid disclosing host paths in persisted tool failure messages.
- Return client errors for malformed run identifiers and inaccessible workspaces.
- Align frontend actions with actual roles; keep sign-out reachable in short and
  mobile layouts; hide approval controls after terminal states.
- Add focused security, API and real-browser regressions with isolated fixtures.

RAG, long-term retrieval, arbitrary workflow graphs and verified Qwen-driven
self-correction remain unfinished. This entry does not announce a production release.
