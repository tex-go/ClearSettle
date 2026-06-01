# Architecture Context

High-level: Feature-based architecture with backend services (FastAPI) and frontend (React) served via Nginx. PostgreSQL as canonical store. Playwright used for discovery/automation.

Non-functional goals
- Scalability for increasing marketplaces and seller volume.
- Observability: metrics, logs and tracing for critical flows (parsing, reconciliation, settlements).
