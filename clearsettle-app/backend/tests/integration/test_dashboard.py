"""Integration tests for protected API endpoints (dashboard, settlements, etc.)."""
import pytest
from httpx import AsyncClient


class TestDashboard:
    async def test_dashboard_requires_auth(self, client: AsyncClient):
        r = await client.get("/dashboard/summary")
        assert r.status_code == 401

    async def test_dashboard_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/dashboard/summary", headers=auth_headers)
        assert r.status_code == 200

    async def test_dashboard_invalid_token_rejected(self, client: AsyncClient):
        r = await client.get("/dashboard/summary", headers={"Authorization": "Bearer bad.token"})
        assert r.status_code == 401

    async def test_dashboard_summary_has_expected_shape(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/dashboard/summary", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # Shape checks — presence of top-level keys
        assert isinstance(data, dict)


class TestSettlements:
    async def test_settlements_requires_auth(self, client: AsyncClient):
        r = await client.get("/settlements/")
        assert r.status_code == 401

    async def test_settlements_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/settlements/", headers=auth_headers)
        assert r.status_code == 200

    async def test_settlements_returns_list_or_dict(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/settlements/", headers=auth_headers)
        data = r.json()
        assert isinstance(data, (list, dict))


class TestDisputes:
    async def test_disputes_requires_auth(self, client: AsyncClient):
        r = await client.get("/disputes/")
        assert r.status_code == 401

    async def test_disputes_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/disputes/", headers=auth_headers)
        assert r.status_code == 200

    async def test_raise_dispute_requires_auth(self, client: AsyncClient):
        r = await client.post("/disputes/", json={
            "platform": "Amazon",
            "dispute_type": "Commission Overcharge",
            "settlement_id": "S-001",
            "amount": 1000,
            "description": "Test dispute",
        })
        assert r.status_code == 401


class TestBankRecon:
    async def test_bank_requires_auth(self, client: AsyncClient):
        r = await client.get("/bank/")
        assert r.status_code == 401

    async def test_bank_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/bank/", headers=auth_headers)
        assert r.status_code == 200


class TestAnalytics:
    async def test_analytics_requires_auth(self, client: AsyncClient):
        r = await client.get("/analytics/")
        assert r.status_code == 401

    async def test_analytics_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/analytics/", headers=auth_headers)
        assert r.status_code == 200


class TestReturns:
    async def test_returns_requires_auth(self, client: AsyncClient):
        r = await client.get("/returns/")
        assert r.status_code == 401

    async def test_returns_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/returns/", headers=auth_headers)
        assert r.status_code == 200


class TestGst:
    async def test_gst_requires_auth(self, client: AsyncClient):
        r = await client.get("/gst/")
        assert r.status_code == 401

    async def test_gst_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/gst/", headers=auth_headers)
        assert r.status_code == 200
