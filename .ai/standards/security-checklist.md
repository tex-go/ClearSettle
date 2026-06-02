# Security Agent — Quick Guidance

This file contains quick security review checklist for agents to consume.

- Validate all file uploads: size, type, scanning, sandbox parsing.
- Ensure endpoints require auth and correct RBAC checks.
- Use parameterized queries and avoid raw string SQL.
- Secrets must be stored in vault or environment variables, never in repo.
- Enforce rate limits on heavy APIs (parsing, discovery).
