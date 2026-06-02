# Database Safety Standards
**Version:** 1.0 | **Owner:** `database-agent`

Financial data is immutable. Migrations are irreversible without a plan. This document defines the standards that prevent data loss, schema drift, and undetected corruption in ClearSettle's PostgreSQL database.

---

## Migration Safety Rules

### Mandatory for Every Migration

1. **Test both directions** — `alembic upgrade head` AND `alembic downgrade -1` must succeed on a clean database.
2. **Idempotent operations** — Use `IF NOT EXISTS`, `ON CONFLICT DO NOTHING` wherever possible.
3. **Column name must match ORM model** — verify against `app/db/models/` before writing INSERT statements in migrations.
4. **Seed data must use correct column names** — mismatches cause startup failures (proven by migration 033 incident).
5. **Insert order respects FK constraints** — insert parent rows before child rows (e.g., users before companies).
6. **No raw SQL string interpolation** — use `sa.text()` with named parameters.
7. **No migration may exceed 30 seconds** — batch large updates.
8. **Never modify committed migrations** — create a new migration instead.

### Migration Validation Sequence

Run this sequence in staging before every production deploy:

```bash
# Step 1: Clean state test
docker compose exec postgres psql -U clearsettle_user -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
# Expected: exits 0, all tables exist

# Step 2: Rollback test
alembic downgrade -1
# Expected: exits 0, previous state restored

# Step 3: Re-upgrade test
alembic upgrade head
# Expected: exits 0, idempotent

# Step 4: Seed validation
alembic current
# Expected: shows head revision
```

### Destructive Operation Protocol

Any migration that:
- Drops a column
- Drops a table
- Changes a column's NOT NULL constraint
- Removes a foreign key

...requires:

1. A prior migration that adds a deprecation notice (e.g., rename column to `_deprecated_column`)
2. At minimum **one release cycle** between deprecation and removal
3. `architect-agent` approval
4. Data migration plan to move existing data

---

## Schema Drift Detection

Run monthly:
```bash
alembic check
# Must return: No new upgrade operations detected.
```

If drift is detected (ORM model differs from DB schema), it means:
- Someone modified the DB directly — investigate who and why
- A migration was applied that doesn't match the code — create correction migration
- A model was changed without a migration — create the missing migration

Schema drift in production is a CRITICAL incident.

---

## Data Integrity Constraints

### Required on All Financial Tables
```sql
-- Immutability: prevent direct UPDATE on confirmed records
-- Implement via application-layer check, not DB constraint
-- Status: pending → confirmed → settled (one-way state machine)

-- Audit columns required on all financial tables:
created_at     TIMESTAMP NOT NULL DEFAULT NOW()
updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
created_by     UUID REFERENCES users(id)   -- who/what created this record
source         VARCHAR(100)                 -- 'flipkart_report' | 'amazon_spapi' | 'manual'
provenance     JSONB                        -- raw source reference

-- Soft delete: never hard-delete financial records
deleted_at     TIMESTAMP                   -- NULL = active, SET = soft-deleted
```

### Required Indexes
```sql
-- Every foreign key must have an index
CREATE INDEX CONCURRENTLY idx_{table}_{column} ON {table}({column});

-- Every timestamp-filtered query column must have an index
CREATE INDEX CONCURRENTLY idx_{table}_created_at ON {table}(created_at);

-- Multi-tenant: company_id must always be indexed
CREATE INDEX CONCURRENTLY idx_{table}_company_id ON {table}(company_id);
```

### Constraint Naming Convention
```sql
-- Primary keys:   pk_{table}
-- Foreign keys:   fk_{table}_{ref_table}_{column}
-- Unique:         uq_{table}_{column(s)}
-- Check:          ck_{table}_{condition}
-- Index:          idx_{table}_{column(s)}
```

---

## Backup Policy

| Environment | Backup Frequency | Retention | Tested |
|---|---|---|---|
| Production | Daily full + hourly WAL | 30 days | Monthly restore test |
| Staging | Daily full | 7 days | Before every release |
| Development | On-demand | Local only | — |

Backup restore must be tested before every major release. `devops-agent` owns backup execution. `database-agent` owns restore validation.

---

## Seed Data Safety

Production seed data (marketplace registry, super-admin) must:
- Use `ON CONFLICT DO NOTHING` — never overwrite existing production data
- Check for existence before insert: `SELECT id FROM users WHERE email = :email`
- Use correct column names verified against ORM model
- Not contain default passwords in production environments (raise error if default credentials used)

---

## Query Performance Standards

- No unbounded queries — all list endpoints must have `LIMIT` + `OFFSET` or cursor pagination
- No `SELECT *` in production code — always specify columns
- N+1 queries are forbidden — use `selectin` or `joined` loading
- Queries touching > 10,000 rows require explicit performance review by `database-agent`
- Slow query threshold: 200ms — queries above this are logged and reviewed
