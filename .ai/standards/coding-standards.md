# Coding Standards

Scope: All language stacks in ClearSettle.

Key rules
- Prefer readable, well-named functions; follow SOLID principles.
- Keep functions < 120 lines; classes focused on single responsibility.
- Avoid deep nesting; fail-fast and early return patterns.
- Use typed interfaces and Pydantic models for external data boundaries.

Pull Request checklist
- Tests added/updated
- Lint passed
- Peer review by domain agent (e.g., `architect-agent` for infra changes)
