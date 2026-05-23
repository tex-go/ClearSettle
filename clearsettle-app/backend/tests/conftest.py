"""
Shared fixtures for the ClearSettle test suite.

Lifespan background tasks (discovery_scheduler, run_reminder_scheduler) are
patched to prevent real external service calls during tests.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


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
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    mock_scheduler = MagicMock()
    mock_scheduler.start = AsyncMock()
    mock_scheduler.stop = AsyncMock()

    with (
        # discovery_scheduler is now a module-level attribute on app.main
        patch("app.main.discovery_scheduler", mock_scheduler),
        # Prevent the reminder loop from running as a background task
        patch("app.services.meetings.reminder_store.run_reminder_scheduler", AsyncMock()),
    ):
        from app.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac


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
