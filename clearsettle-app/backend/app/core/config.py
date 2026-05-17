from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── JWT ──────────────────────────────────────────────────────────────────
    secret_key: str = "clearsettle-secret-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ── Database ─────────────────────────────────────────────────────────────
    # postgresql+psycopg2://user:password@host:5432/dbname
    # Leave empty to run without a DB (mock-data mode)
    database_url: str = ""

    # ── Credential encryption ─────────────────────────────────────────────────
    # 32-byte URL-safe base64 Fernet key.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # ── Amazon SP API ─────────────────────────────────────────────────────────
    # Register your app at https://sellercentral.amazon.in → Apps & Services → Develop Apps
    sp_api_app_id: str = ""          # Application ID (amzn1.sellerapps.app.xxx)
    sp_api_client_id: str = ""       # LWA Client ID (amzn1.application-oa2-client.xxx)
    sp_api_client_secret: str = ""   # LWA Client Secret

    # Must match the Redirect URI registered in the developer console
    sp_api_redirect_uri: str = ""

    # India marketplace
    sp_api_marketplace_id: str = "A21TJRUUN4KGV"
    sp_api_region: str = "eu"        # na | eu | fe  (India is under EU region)
    sp_api_endpoint: str = "https://sellingpartnerapi-eu.amazon.com"

    # ── App ───────────────────────────────────────────────────────────────────
    env: str = "development"
    frontend_url: str = "http://localhost:80"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
