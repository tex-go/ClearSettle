"""Integration tests for root, health, and status endpoints."""
import pytest
from httpx import AsyncClient


class TestRootEndpoint:
    async def test_root_returns_200(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code == 200

    async def test_root_contains_service_name(self, client: AsyncClient):
        r = await client.get("/")
        data = r.json()
        assert data["service"] == "ClearSettle API"

    async def test_root_contains_status(self, client: AsyncClient):
        r = await client.get("/")
        assert r.json()["status"] == "online"

    async def test_root_contains_docs_link(self, client: AsyncClient):
        r = await client.get("/")
        assert "/docs" in r.json()["docs"]


class TestHealthEndpoint:
    async def test_health_returns_200(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_status_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.json()["status"] == "ok"

    async def test_health_has_database_field(self, client: AsyncClient):
        r = await client.get("/health")
        assert "database" in r.json()


class TestStatusEndpoint:
    async def test_status_returns_200(self, client: AsyncClient):
        r = await client.get("/status")
        assert r.status_code == 200

    async def test_status_has_required_fields(self, client: AsyncClient):
        data = r = await client.get("/status")
        body = r.json()
        assert "service" in body
        assert "version" in body
        assert "database" in body

    async def test_status_service_name(self, client: AsyncClient):
        r = await client.get("/status")
        assert r.json()["service"] == "ClearSettle API"


class TestSecurityHeaders:
    async def test_x_content_type_options(self, client: AsyncClient):
        r = await client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, client: AsyncClient):
        r = await client.get("/")
        assert r.headers.get("x-frame-options") == "DENY"

    async def test_x_xss_protection(self, client: AsyncClient):
        r = await client.get("/")
        assert "1" in r.headers.get("x-xss-protection", "")
