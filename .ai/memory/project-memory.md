# Project Memory — ClearSettle

Architectural Decisions
- Feature-based architecture (modules per feature) adopted to keep service boundaries clear.
- Use FastAPI + SQLAlchemy + asyncpg for backend; Pydantic v2 for validation.

Marketplace Learnings
- Flipkart is the initial priority; parser edge-cases are common (merged headers, missing columns).

Settlement Rules
- Canonical models: `Order`, `Settlement`, `Fee`, `Tax`, `Refund`, `Adjustment`.
- All calculations are recorded with input provenance and `reconciliation_agent` version.

Technical Debt
- Improve test coverage in reconciliation modules; refactor large monolithic modules into services.

Future Roadmap
- Amazon SP API integration, mobile clients (Flutter), AI anomaly detection models.
