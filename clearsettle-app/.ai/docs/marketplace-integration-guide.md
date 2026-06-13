# ClearSettle Marketplace Integration Framework

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Router                         │
│                 /marketplace/*                           │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    Service Layer           │
         │  connection_service        │
         │  oauth_service             │
         │  token_service             │
         │  sync_manager              │
         │  audit_service             │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │   Provider Registry        │
         │  get_provider(slug)        │
         └─────────────┬─────────────┘
                       │
    ┌──────────────────┼───────────────────────┐
    │                  │                        │
    ▼                  ▼                        ▼
AmazonProvider  ShopifyProvider   WooCommerceProvider  ...
(OAuth LWA)     (OAuth 2.0)       (API Key+Secret)
```

## Database Schema

```
marketplaces                → Static platform catalog (seeded in migration 033)
marketplace_connections     → Per-company connection (status, seller info, sync stats)
marketplace_credentials     → Fernet-encrypted tokens and keys (isolated table)
marketplace_accounts        → Account info fetched from marketplace API
marketplace_sync_jobs       → Sync job lifecycle
marketplace_sync_logs       → Structured per-job event log
oauth_states                → Short-lived CSRF state tokens (TTL: 10 minutes)
marketplace_audit_logs      → Immutable audit trail
```

## Connection Types

| Type | Example Platforms | Flow |
|------|-------------------|------|
| `oauth` | Amazon, Shopify, eBay | Redirect → Authorize → Callback → Token exchange |
| `api_key_secret` | WooCommerce, Walmart | Form: store URL + consumer key + secret |
| `api_key` | Custom platforms | Form: single API key |
| `manual_upload` | Flipkart, Meesho, Myntra, AJIO | One-click enable → upload reports manually |
| `partner_api` | Future integrations | Provider-specific |

## Adding a New Marketplace

### Step 1: Create the provider

```python
# app/services/marketplace/providers/mynewmarket.py
from app.services.marketplace.abstract_provider import AbstractMarketplaceProvider, ConnectionType

class MyNewMarketProvider(AbstractMarketplaceProvider):
    @property
    def marketplace_slug(self) -> str:
        return "mynewmarket"

    @property
    def connection_type(self) -> str:
        return ConnectionType.OAUTH   # or API_KEY, MANUAL_UPLOAD, etc.

    async def get_authorization_url(self, state, redirect_uri, connection, **kw) -> str:
        return f"https://mynewmarket.com/oauth?state={state}&redirect_uri={redirect_uri}"

    async def handle_callback(self, code, connection, credentials, **kw):
        # Exchange code for tokens
        # Store encrypted tokens using self.store_oauth_tokens(credentials, tokens)
        ...

    async def refresh_tokens(self, connection, credentials):
        ...

    async def validate_connection(self, connection, credentials):
        ...

    async def get_account_details(self, connection, credentials):
        ...

    async def disconnect(self, connection, credentials):
        ...

    async def start_sync(self, connection, credentials, sync_job):
        ...
```

### Step 2: Register in provider_registry.py

```python
from app.services.marketplace.providers.mynewmarket import MyNewMarketProvider

PROVIDER_REGISTRY = {
    ...
    "mynewmarket": MyNewMarketProvider,
}
```

### Step 3: Add to database seed (migration 034)

```python
{
    "slug": "mynewmarket",
    "name": "My New Market",
    "connection_type": "oauth",
    "is_live": True,
    ...
}
```

**That's all.** No router changes, no service changes, no model changes.

## Amazon SP-API Setup

### Required Environment Variables

```bash
SP_API_APP_ID=amzn1.sellerapps.app.xxxxx
SP_API_CLIENT_ID=amzn1.application-oa2-client.xxxxx
SP_API_CLIENT_SECRET=<your_client_secret>
SP_API_REDIRECT_URI=https://app.clearsettle.in/marketplace/oauth/callback
SP_API_MARKETPLACE_ID=A21TJRUUN4KGV  # India
SP_API_REGION=eu
SP_API_ENDPOINT=https://sellingpartnerapi-eu.amazon.com
```

### OAuth Flow

```
1. Seller clicks "Connect Amazon"
2. POST /marketplace/oauth/initiate  → { authorization_url, state }
3. App redirects to authorization_url (Seller Central)
4. Seller grants permission
5. Amazon redirects to /marketplace/oauth/callback?code=XXX&state=YYY
6. Backend validates state → exchanges code for LWA tokens
7. Tokens encrypted with Fernet and stored in marketplace_credentials
8. GET /sellers/v1/marketplaceParticipations called to get seller info
9. Connection status → "connected"
```

## Shopify Setup

```bash
SHOPIFY_API_KEY=<your_partner_app_api_key>
SHOPIFY_API_SECRET=<your_partner_app_api_secret>
SHOPIFY_REDIRECT_URI=https://app.clearsettle.in/marketplace/oauth/callback
SHOPIFY_SCOPES=read_orders,read_finances,read_products,read_inventory
```

### Required: Seller's shop domain

When initiating Shopify OAuth, the seller must provide their store subdomain:
```
POST /marketplace/oauth/initiate
{ "marketplace_slug": "shopify", "shop_domain": "mystore.myshopify.com" }
```

## WooCommerce Setup

No environment variables needed. Each seller provides their own:
- Store URL (e.g. `https://mystore.com`)
- Consumer Key (generated in WordPress → WooCommerce → Settings → API)
- Consumer Secret

```
POST /marketplace/connections/credentials
{
  "marketplace_slug": "woocommerce",
  "credentials": {
    "store_url": "https://mystore.com",
    "consumer_key": "ck_xxxx",
    "consumer_secret": "cs_xxxx"
  }
}
```

## Super Admin

### Seed credentials

```bash
SUPER_ADMIN_EMAIL=Admin@clearsettle.com     # default
SUPER_ADMIN_PASSWORD=Admin@123              # CHANGE THIS IN PRODUCTION
SUPER_ADMIN_NAME=ClearSettle Admin
```

Set these in `.env` BEFORE running `alembic upgrade head`.

### Super Admin capabilities

- `GET /marketplace/admin/connections` — view all connections across all companies
- `GET /admin/...` — existing admin routes
- RBAC: `is_superadmin = True` on the User row

## Security Architecture

### Credential storage

All sensitive credentials are Fernet-encrypted (AES-128-CBC + HMAC-SHA256):

```python
from app.core.crypto import encrypt, decrypt

# Write
credentials.access_token_enc = encrypt(access_token)

# Read
access_token = decrypt(credentials.access_token_enc)
```

The encryption key is set via `ENCRYPTION_KEY` environment variable.
Columns ending in `_enc` are ALWAYS encrypted. Never read/write them raw.

### OAuth CSRF protection

1. `create_oauth_state()` generates a `secrets.token_urlsafe(32)` state token
2. State is persisted in `oauth_states` with a 10-minute TTL
3. `handle_oauth_callback()` validates state against DB:
   - state must exist
   - state must not be expired
   - state must not have been used before (replay protection)
4. State is marked `used_at = now()` immediately on first use

### Audit logging

Every significant action writes an immutable record to `marketplace_audit_logs`:
- `connection.created` / `connection.connected` / `connection.disconnected`
- `oauth.initiated` / `oauth.callback` / `oauth.token_refreshed`
- `sync.started` / `sync.completed` / `sync.failed`
- `credential.updated`

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/marketplace/` | List all marketplace platforms |
| GET | `/marketplace/connections/` | List company's connections |
| GET | `/marketplace/connections/{id}` | Single connection detail |
| POST | `/marketplace/connections/manual` | Connect manual-upload platform |
| POST | `/marketplace/connections/credentials` | Connect API-key platform |
| DELETE | `/marketplace/connections/{slug}` | Disconnect platform |
| POST | `/marketplace/oauth/initiate` | Start OAuth flow |
| GET/POST | `/marketplace/oauth/callback` | OAuth redirect target |
| POST | `/marketplace/connections/{id}/sync` | Trigger sync |
| GET | `/marketplace/connections/{id}/jobs` | List sync jobs |
| POST | `/marketplace/connections/{id}/validate` | Live credential check |
| GET | `/marketplace/audit/{id}` | Audit log for connection |
| GET | `/marketplace/admin/connections` | Super admin: all connections |
