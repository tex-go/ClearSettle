# React Standards

Component design
- Prefer small, focused components and composition.
- Presentational components separated from container logic.

State
- Use `zustand` for global state; prefer hooks for local state.

Accessibility
- ARIA roles for interactive elements; keyboard navigation for main flows.

Testing
- Use `@testing-library/react` and Vitest; test user flows not implementation.
