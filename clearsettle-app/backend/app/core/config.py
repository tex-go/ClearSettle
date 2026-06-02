"""
app/core/config.py — Production-hardened settings.

Security principles:
  - SECRET_KEY has NO hardcoded default. An ephemeral key is generated in
    development (with a loud warning). Production fails hard if not set.
  - DATABASE_URL and ENCRYPTION_KEY are required in production.
  - Access tokens expire in 30 minutes (was 24 hours).
  - Refresh tokens expire in 7 days (was 30 days).
  - CORS is restricted to explicit frontend origins (never wildcard in prod).

Generate secrets:
  SECRET_KEY   : python -c "import secrets; print(secrets.token_hex(64))"
  ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import logging
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ── Environment ───────────────────────────────────────────────────────────
    env: Literal["development", "staging", "production"] = "development"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ── JWT / Security ────────────────────────────────────────────────────────
    # REQUIRED in production. No hardcoded default — ever.
    secret_key: str = ""
    algorithm: str = "HS256"
    # 30 minutes — access tokens are short-lived by design.
    # The frontend silently refreshes using the refresh token.
    access_token_expire_minutes: int = 30
    # 7 days — balance between UX and security.
    refresh_token_expire_days: int = 7

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = ""

    # ── Credential encryption (Fernet AES-128-CBC + HMAC) ────────────────────
    encryption_key: str = ""

    # ── Email (SMTP or SendGrid) ──────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@clearsettle.in"
    smtp_from_name: str = "ClearSettle"
    smtp_tls: bool = True
    sendgrid_api_key: str = ""

    # ── Auth flow timing ──────────────────────────────────────────────────────
    password_reset_expire_minutes: int = 15
    email_verification_expire_hours: int = 24
    invitation_expire_days: int = 7

    # ── Brute-force / rate limiting ───────────────────────────────────────────
    login_max_attempts: int = 5           # per window before lockout
    login_lockout_seconds: int = 900      # 15 min lockout after max_attempts failures
    login_rate_window_seconds: int = 300  # 5-min sliding window

    # ── Amazon SP API ─────────────────────────────────────────────────────────
    sp_api_app_id: str = ""
    sp_api_client_id: str = ""
    sp_api_client_secret: str = ""
    sp_api_redirect_uri: str = ""
    sp_api_refresh_token: str = ""
    sp_api_marketplace_id: str = "A21TJRUUN4KGV"
    sp_api_region: str = "eu"
    sp_api_endpoint: str = "https://sellingpartnerapi-eu.amazon.com"

    # ── Super Admin ───────────────────────────────────────────────────────────
    # Credentials for the platform super-admin seeded in migration 033.
    # NEVER hardcode real passwords here — override via environment variables.
    super_admin_email:    str = "Admin@clearsettle.com"
    super_admin_password: str = "Admin@123"
    super_admin_name:     str = "ClearSettle Admin"

    # ── Marketplace Integration Framework ─────────────────────────────────────
    # Shopify OAuth
    shopify_api_key:      str = ""
    shopify_api_secret:   str = ""
    shopify_redirect_uri: str = ""
    shopify_scopes:       str = "read_orders,read_finances,read_products,read_inventory"

    # WooCommerce (per-store — base URL is set per-connection, not globally)
    woocommerce_api_version: str = "wc/v3"

    # Marketplace sync behaviour
    marketplace_sync_interval_minutes:         int   = 60
    marketplace_max_sync_retry:                int   = 3
    marketplace_access_token_refresh_buffer_m: int   = 5
    marketplace_oauth_state_ttl_minutes:       int   = 10

    # ── Seller Discovery Engine ───────────────────────────────────────────────
    anthropic_api_key: str = ""
    scraper_proxy_url: str = ""
    discovery_max_leads_per_job: int = 500
    discovery_rate_limit_rps: float = 0.5
    discovery_max_concurrent_jobs: int = 2
    discovery_crawl_interval_hours: float = 24.0

    @model_validator(mode="before")
    @classmethod
    def enforce_production_requirements_and_fill_dev_defaults(cls, data: dict) -> dict:
        """
        - Production: fail fast if critical secrets are missing.
        - Development: generate an ephemeral SECRET_KEY with a loud warning.
        """
        env = data.get("env", "development")
        is_production = env == "production"

        # ── SECRET_KEY ────────────────────────────────────────────────────────
        secret_key = data.get("secret_key", "")
        if not secret_key:
            if is_production:
                raise ValueError(
                    "[FATAL] SECRET_KEY must be set in production.\n"
                    "Generate: python -c \"import secrets; print(secrets.token_hex(64))\""
                )
            # Development: ephemeral key — loud warning so devs notice
            ephemeral = secrets.token_hex(64)
            data["secret_key"] = ephemeral
            logger.warning(
                "\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  WARNING: SECRET_KEY not set — using an EPHEMERAL key.       ║\n"
                "║  All existing JWTs become INVALID on every restart.          ║\n"
                "║  Set SECRET_KEY in your .env file for development stability. ║\n"
                "╚══════════════════════════════════════════════════════════════╝"
            )
        elif len(secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long.\n"
                "Generate: python -c \"import secrets; print(secrets.token_hex(64))\""
            )

        # ── DATABASE_URL ──────────────────────────────────────────────────────
        if is_production and not data.get("database_url", ""):
            raise ValueError("[FATAL] DATABASE_URL must be set in production.")

        # ── ENCRYPTION_KEY ────────────────────────────────────────────────────
        if is_production and not data.get("encryption_key", ""):
            raise ValueError(
                "[FATAL] ENCRYPTION_KEY must be set in production.\n"
                "Generate: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )

        return data

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def allowed_origins(self) -> list[str]:
        """
        CORS allowed origins.
        Production: ONLY the configured frontend_url. Never wildcard.
        Development: common local ports for convenience.
        """
        if self.is_production:
            return [o for o in [self.frontend_url] if o]
        return [
            self.frontend_url,
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:80",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
