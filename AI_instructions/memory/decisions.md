# Architectural Decisions

## Frontend
- Zustand instead of Redux (simpler, no boilerplate)
- No TailwindCSS (custom inline styles, no design system coupling)
- No external UI kits (full control over accessibility and dark theme)
- Recharts for data visualization
- Vite build tooling
- Vitest + @testing-library/react for unit/component tests
- Playwright for E2E / smoke tests

## Backend
- FastAPI with router-based modular architecture
- SQLAlchemy 2.0 async + asyncpg for DB
- PostgreSQL (production) with Alembic migrations
- Mock-data fallback when DATABASE_URL is not set
- JWT HS256 access tokens + opaque SHA-256 refresh tokens + JTI revocation
- bcrypt rounds=12 for password hashing
- Multi-tenant isolation via company_id on every query
- pytest-asyncio asyncio_mode=auto + asyncio_loop_scope=session for test stability

## Infrastructure
- Docker-first architecture
- Nginx reverse proxy
- Ollama (local LLM inference)
- Flowise (AI workflow builder)

## Versioning & Release
- SemVer (MAJOR.MINOR.PATCH) via VERSION file at repo root
- Conventional commits (feat/fix/chore/ci/docs/test/refactor/perf)
- Tag vX.Y.Z → release.yml → GitHub Release + production deploy
- scripts/tag-release.sh for developer-triggered releases
- Staging auto-deploys on dev CI pass; production is tag-gated only

## Core Non-Negotiables
- No Tailwind, no external UI kits
- Docker-compatible architecture only
- No nested template literals
- Use function declarations (not arrow functions in components)
- Never silently break APIs
- No architecture rewrites without architecture-agent review
- No random dependencies
