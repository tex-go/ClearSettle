# Observability Standards
**Version:** 1.0 | **Owner:** `devops-agent` + `backend-agent`

Observability is how we know ClearSettle is working correctly. For financial software, silent failures are worse than noisy ones. Every critical operation must be observable.

---

## Structured Logging

### Log Format (Backend)
All backend logs must be structured JSON:
```json
{
  "timestamp": "2026-06-01T08:15:00.000Z",
  "level": "INFO",
  "service": "clearsettle-backend",
  "version": "1.0.0",
  "request_id": "uuid",
  "user_id": "uuid-or-null",
  "company_id": "uuid-or-null",
  "event": "reconciliation.started",
  "data": {
    "marketplace": "flipkart",
    "report_id": "uuid",
    "order_count": 1234
  },
  "duration_ms": 0
}
```

### Log Levels
| Level | When To Use |
|---|---|
| `ERROR` | Exceptions that affect user experience or data integrity |
| `WARN` | Unexpected but recoverable situations |
| `INFO` | Key business events (login, upload, reconciliation complete) |
| `DEBUG` | Detailed technical events (only in development) |

### Mandatory Log Events

| Event | Level | Required Fields |
|---|---|---|
| User login success | INFO | user_id, company_id |
| User login failure | WARN | email (masked), attempt_count |
| File upload received | INFO | filename, size_bytes, marketplace |
| Reconciliation started | INFO | report_id, order_count |
| Reconciliation complete | INFO | discrepancy_count, total_discrepancy_amount |
| Discrepancy detected | INFO | order_id, amount, discrepancy_type |
| Dispute filed | INFO | dispute_id, amount, marketplace |
| Migration executed | INFO | revision, duration_ms |
| Unhandled exception | ERROR | exception_type, message, stack_trace |
| Database query slow | WARN | query_hash, duration_ms, table |
| Rate limit triggered | WARN | endpoint, user_id, attempt_count |

### Never Log
- Passwords (even hashed)
- JWT tokens
- Encryption keys
- Full credit card or payment data
- PII beyond what's operationally necessary (mask emails after @)

---

## Audit Trail

Every financial operation must produce an immutable audit record:

```python
# audit_log table (required columns)
{
  "id": UUID,
  "timestamp": datetime,
  "event_type": str,          # 'settlement.imported' | 'dispute.filed' | 'reconciliation.run'
  "user_id": UUID,            # who triggered
  "company_id": UUID,         # which company
  "entity_type": str,         # 'Settlement' | 'Dispute' | 'ReconciliationRun'
  "entity_id": UUID,          # which entity
  "before_state": JSONB,      # state before change (null for creates)
  "after_state": JSONB,       # state after change
  "ip_address": str,          # request origin
  "user_agent": str,          # client info
  "metadata": JSONB           # additional context
}
```

Audit logs are:
- Immutable (no UPDATE or DELETE ever)
- Retained for 7 years (financial compliance requirement)
- Indexed by company_id + timestamp

---

## Business Metrics

Track these metrics per company per period:

```
Reconciliation metrics:
- reconciliation_runs_total (counter)
- discrepancies_detected_total (counter)
- discrepancy_amount_inr (gauge, per marketplace)
- disputes_filed_total (counter)
- disputes_resolved_total (counter)
- recovery_amount_inr (gauge)
- commission_overcharge_amount_inr (gauge)
- gst_recoverable_amount_inr (gauge)

Report metrics:
- reports_uploaded_total (counter, per marketplace)
- report_processing_duration_seconds (histogram)
- report_parsing_errors_total (counter)

User metrics:
- active_users_daily (gauge)
- login_attempts_total (counter)
- login_failures_total (counter)
```

---

## Infrastructure Metrics

| Metric | Source | Alert If |
|---|---|---|
| CPU utilization | Container stats | > 80% sustained 5 min |
| Memory usage | Container stats | > 85% of limit |
| DB connection pool | SQLAlchemy | > 80% utilized |
| DB query duration (p99) | Slow query log | > 500ms |
| HTTP response time (p99) | Nginx logs | > 2000ms |
| Error rate (5xx) | Nginx logs | > 0.1% |
| Disk usage | Host metrics | > 80% |
| SSL certificate expiry | certbot | < 14 days remaining |

---

## Error Tracking

All unhandled exceptions must be captured with:
- Full stack trace
- Request context (URL, method, user_id, company_id)
- Environment (version, host)
- Frequency (deduplicate within 1-hour window)

Implementation: integrate Sentry or equivalent error tracking (`devops-agent` task).

---

## Alerting Policy

| Severity | Condition | Response Time | Alert Channel |
|---|---|---|---|
| P0 Critical | Service down, data loss risk | 5 minutes | All channels |
| P1 High | Error rate > 1%, financial calculation error | 15 minutes | Slack + email |
| P2 Medium | Slow response, coverage drop, disk > 80% | 1 hour | Slack |
| P3 Low | Non-critical degradation, warnings | Next business day | Email digest |
