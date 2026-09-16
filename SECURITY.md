# Security policy

AgentFlow is a development-stage local agent platform, not a hardened hostile
multi-tenant service. See [security boundaries](docs/security.md) and
[implementation status](docs/implementation-status.md) before deployment.

Report suspected approval bypass, workspace escape, secret disclosure, command
execution, or authentication flaws privately to the repository maintainer. Use
GitHub private vulnerability reporting if available; otherwise ask the maintainer
for a private contact channel without posting exploit details or credentials in a
public issue. No response-time or bounty commitment is currently published.

Include the affected revision, a minimal non-sensitive reproduction, expected and
observed behavior, and impact. Use disposable workspaces and synthetic credentials.
Never test against another person's projects or systems without authorization.

Only the current development branch is maintained; there is no supported stable
release line. Keep changes and advisories explicit about what was actually tested.
