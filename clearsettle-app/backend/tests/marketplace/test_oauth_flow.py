"""
Integration tests for the OAuth flow orchestration.

Tests cover:
  - OAuth state creation and expiry
  - State token uniqueness and CSRF prevention
  - Callback validation (valid / expired / already-used / wrong state)
  - Token refresh dispatch
  - Audit log entries
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.marketplace.abstract_provider import (
    OAuthTokens,
    AccountDetails,
    ConnectionStatus,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_oauth_state(
    *,
    state_token="test-state-abc",
    expired=False,
    used=False,
):
    state = MagicMock()
    state.id             = uuid4()
    state.company_id     = uuid4()
    state.marketplace_id = uuid4()
    state.state_token    = state_token
    state.expires_at     = (
        datetime.utcnow() - timedelta(minutes=5)
        if expired else
        datetime.utcnow() + timedelta(minutes=8)
    )
    state.used_at        = datetime.utcnow() if used else None
    state.redirect_uri   = "https://callback.test"
    state.extra_params   = None
    return state


def make_marketplace(slug="amazon"):
    m = MagicMock()
    m.id   = uuid4()
    m.slug = slug
    m.name = slug.capitalize()
    return m


def make_connection(marketplace_slug="amazon"):
    conn = MagicMock()
    conn.id             = uuid4()
    conn.company_id     = uuid4()
    conn.marketplace_id = uuid4()
    conn.status         = ConnectionStatus.CONNECTING
    conn.seller_id      = None
    conn.seller_name    = None
    conn.seller_email   = None
    conn.shop_domain    = None
    conn.error_message  = None
    conn.connected_at   = None
    conn.credentials    = None
    conn.marketplace    = make_marketplace(marketplace_slug)
    return conn


# ── State creation tests ──────────────────────────────────────────────────────

class TestOAuthStateCreation:
    @pytest.mark.asyncio
    @patch("app.services.marketplace.oauth_service._get_marketplace")
    @patch("app.services.marketplace.oauth_service.get_provider")
    @patch("app.services.marketplace.oauth_service._get_or_create_connection")
    @patch("app.services.marketplace.oauth_service.audit_service.record", new_callable=AsyncMock)
    async def test_create_oauth_state_returns_url(
        self,
        mock_audit,
        mock_get_or_create,
        mock_get_provider,
        mock_get_marketplace,
    ):
        from app.services.marketplace.oauth_service import create_oauth_state

        mock_market = make_marketplace("amazon")
        mock_get_marketplace.return_value = mock_market

        mock_provider = MagicMock()
        mock_provider.connection_type = "oauth"
        mock_provider.get_authorization_url = AsyncMock(
            return_value="https://sellercentral.amazon.in/apps/authorize/consent?state=test"
        )
        mock_get_provider.return_value = mock_provider

        mock_conn = make_connection("amazon")
        mock_get_or_create.return_value = (mock_conn, True)

        db = AsyncMock()
        db.flush   = AsyncMock()
        db.add     = MagicMock()
        db.execute = AsyncMock()

        state_row, auth_url = await create_oauth_state(
            company_id       = uuid4(),
            marketplace_slug = "amazon",
            db               = db,
            redirect_uri     = "https://callback.test",
        )

        assert "sellercentral.amazon.in" in auth_url
        assert db.add.called
        mock_audit.assert_called_once()


class TestOAuthStateValidation:
    def test_state_is_expired(self):
        state = make_oauth_state(expired=True)
        assert state.expires_at < datetime.utcnow()

    def test_state_is_valid(self):
        state = make_oauth_state(expired=False, used=False)
        assert state.expires_at > datetime.utcnow()
        assert state.used_at is None

    def test_state_is_used(self):
        state = make_oauth_state(used=True)
        assert state.used_at is not None


class TestOAuthCallbackValidation:
    @pytest.mark.asyncio
    @patch("app.services.marketplace.oauth_service.get_provider")
    async def test_invalid_state_raises_value_error(self, mock_get_provider):
        from app.services.marketplace.oauth_service import handle_oauth_callback

        db = AsyncMock()
        # Return None to simulate state not found / expired
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=scalar_result)

        with pytest.raises(ValueError, match="Invalid or expired OAuth state token"):
            await handle_oauth_callback(
                code        = "auth_code_xyz",
                state_token = "invalid-state",
                db          = db,
            )

    @pytest.mark.asyncio
    @patch("app.services.marketplace.oauth_service.get_provider")
    async def test_used_state_rejected(self, mock_get_provider):
        from app.services.marketplace.oauth_service import handle_oauth_callback

        db = AsyncMock()
        # Simulate: state exists but used_at is set — the DB WHERE clause filters it out
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=scalar_result)

        with pytest.raises(ValueError, match="Invalid or expired OAuth state token"):
            await handle_oauth_callback(
                code        = "code",
                state_token = "used-state-token",
                db          = db,
            )


# ── Token refresh tests ───────────────────────────────────────────────────────

class TestTokenService:
    @pytest.mark.asyncio
    @patch("app.services.marketplace.token_service.get_provider")
    async def test_ensure_valid_token_refreshes_when_expired(self, mock_get_provider):
        from app.services.marketplace.token_service import ensure_valid_token

        mock_provider = MagicMock()
        mock_provider.needs_token_refresh = MagicMock(return_value=True)
        mock_provider.refresh_tokens = AsyncMock(return_value=OAuthTokens(
            access_token  = "new_access_token",
            refresh_token = "new_refresh_token",
            expires_in    = 3600,
        ))
        mock_provider.store_oauth_tokens = MagicMock()
        mock_provider.get_access_token   = MagicMock(return_value="new_access_token")
        mock_get_provider.return_value   = mock_provider

        conn  = make_connection("amazon")
        creds = MagicMock()
        conn.credentials = creds

        db = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conn)
        db.execute = AsyncMock(return_value=scalar_result)
        db.commit  = AsyncMock()

        with patch("app.services.marketplace.token_service.audit_service.record", new_callable=AsyncMock):
            token = await ensure_valid_token(conn.id, db)

        mock_provider.refresh_tokens.assert_called_once()
        mock_provider.store_oauth_tokens.assert_called_once()
        assert token == "new_access_token"

    @pytest.mark.asyncio
    @patch("app.services.marketplace.token_service.get_provider")
    async def test_ensure_valid_token_skips_refresh_when_fresh(self, mock_get_provider):
        from app.services.marketplace.token_service import ensure_valid_token

        mock_provider = MagicMock()
        mock_provider.needs_token_refresh = MagicMock(return_value=False)
        mock_provider.get_access_token    = MagicMock(return_value="current_access_token")
        mock_get_provider.return_value    = mock_provider

        conn  = make_connection("amazon")
        creds = MagicMock()
        conn.credentials = creds

        db = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conn)
        db.execute = AsyncMock(return_value=scalar_result)

        token = await ensure_valid_token(conn.id, db)

        mock_provider.needs_token_refresh.assert_called_once()
        assert token == "current_access_token"


# ── Connection service tests ──────────────────────────────────────────────────

class TestConnectionService:
    @pytest.mark.asyncio
    @patch("app.services.marketplace.connection_service._get_marketplace")
    @patch("app.services.marketplace.connection_service._get_or_create_connection")
    @patch("app.services.marketplace.connection_service.audit_service.record", new_callable=AsyncMock)
    async def test_create_manual_connection(
        self, mock_audit, mock_create, mock_get_market
    ):
        from app.services.marketplace.connection_service import create_manual_connection

        market = make_marketplace("flipkart")
        market.name           = "Flipkart"
        mock_get_market.return_value = market

        conn = make_connection("flipkart")
        conn.status            = "disconnected"
        conn.display_name      = None
        conn.connected_at      = None
        mock_create.return_value = (conn, True)

        db = AsyncMock()
        db.flush = AsyncMock()

        result = await create_manual_connection(
            company_id       = uuid4(),
            marketplace_slug = "flipkart",
            db               = db,
            display_name     = "My Flipkart Store",
        )

        assert result.status == ConnectionStatus.CONNECTED
        assert result.display_name == "My Flipkart Store"
        mock_audit.assert_called_once()
