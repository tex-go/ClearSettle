"""
Shared fixtures for the ClearSettle test suite.

Async strategy (pytest-asyncio 0.23.x):
  A single event_loop is created for the entire session so that session-scoped
  async fixtures (client, auth_headers) share the same loop as every test.
  Without this, asyncpg connections created in one loop fail with
  "got Future attached to a different loop" when accessed from another.

Lifespan background tasks (discovery_scheduler, run_reminder_scheduler) are
patched to prevent real external service calls during tests.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ── Session-scoped event loop (fixes asyncpg "different loop" errors) ─────────

@pytest.fixture(scope="session")
def event_loop():
    """
    One event loop for the full test session.

    pytest-asyncio 0.23.x requires this override so that session-scoped async
    fixtures (client, auth_headers) and every individual test all run on the
    same loop.  asyncpg connections are loop-bound; sharing the loop prevents
    'got Future attached to a different loop' RuntimeErrors.

    The DeprecationWarning from overriding event_loop is suppressed via the
    filterwarnings setting in pytest.ini.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@clearsettle-test.dev"


VALID_PASSWORD = "TestPass@1234!"
VALID_GSTIN = "33ABCDE1234F1Z5"


def valid_register_payload(**overrides) -> dict:
    base = {
        "email":            unique_email(),
        "phone":            "+91-9876543210",
        "password":         VALID_PASSWORD,
        "confirm_password": VALID_PASSWORD,
        "name":             "Test User",
        "company_name":     "Test Corp Pvt Ltd",
        "gstin":            VALID_GSTIN,
        "state":            "Tamil Nadu",
        "active_platforms": ["Amazon"],
    }
    base.update(overrides)
    return base


# ── App fixture — patches lifespan side-effects ───────────────────────────────

@pytest.fixture(scope="session")
async def client():
    mock_scheduler = MagicMock()
    mock_scheduler.start = AsyncMock()
    mock_scheduler.stop = AsyncMock()

    with (
        patch("app.main.discovery_scheduler", mock_scheduler),
        patch("app.services.meetings.reminder_store.run_reminder_scheduler", AsyncMock()),
    ):
        from app.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac

    # Dispose the DB engine so asyncpg closes all connections cleanly after
    # the session ends, preventing "Event loop is closed" warnings.
    try:
        from app.db.database import engine
        if engine is not None:
            await engine.dispose()
    except Exception:
        pass


# ── Auth fixture — registers + logs in a test user ────────────────────────────

@pytest.fixture(scope="session")
async def auth_headers(client: AsyncClient):
    payload = valid_register_payload()
    reg = await client.post("/auth/register", json=payload)
    # Accept 201 (created) or 200; skip if email already exists (409)
    assert reg.status_code in (200, 201, 409), f"Register failed: {reg.text}"

    login_r = await client.post("/auth/login", json={
        "email": payload["email"],
        "password": payload["password"],
    })
    assert login_r.status_code == 200, f"Login failed: {login_r.text}"
    token = login_r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
