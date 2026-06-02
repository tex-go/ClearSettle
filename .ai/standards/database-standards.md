# Database Standards

Principles
- Use migrations (Alembic) for all schema changes.
- Maintain immutability for ledger-like financial records; append-only event tables where required.

Performance
- Add indexes based on query patterns; consider partitioning for time-series settlement data.

Auditability
- All writes include user_id, source, and file provenance metadata for traceability.
