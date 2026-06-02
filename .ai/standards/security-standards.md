# Security Standards

Must-haves
- Secure secrets (vault/GCP Secret Manager), rotate keys, use env for runtime.
- Validate and sandbox all uploaded files; run parsers in strict resource-limited workers.
- Enforce RBAC and least privilege; audit logs for sensitive operations.

Code review
- Security agent signoff required for any storage, crypto or auth changes.
