"""
app/core/auth.py — PURGED.

This file previously contained:
  - DEMO_USER  (hardcoded admin credentials)
  - SECRET_KEY (hardcoded "clearsettle-secret-2026")
  - create_token / decode_token (duplicates of security.py)

All of those have been removed as part of the enterprise security hardening.

Use these instead:
  app.core.security   → hash_password, verify_password, create_access_token,
                         decode_access_token, generate_refresh_token, ...
  app.services.auth_service → login, register, refresh_tokens, logout,
                               forgot_password, reset_password, ...
"""
# Intentionally empty — no DEMO_USER, no hardcoded secrets.
# Any import of DEMO_USER from this module is a bug: remove it and use the DB.
