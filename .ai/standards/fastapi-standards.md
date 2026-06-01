# FastAPI Standards

Architecture
- Routes only glue to service layer; no business logic in routes.
- Use dependency injection for DB sessions and config.

Async rules
- All IO in async endpoints must use async libraries; avoid blocking code.

Testing
- Unit tests for services, integration tests for routers using TestClient/async clients.

API Design
- Use OpenAPI types, clear status codes, consistent pagination and error schema.
