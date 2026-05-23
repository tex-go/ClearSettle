"""Integration tests for /auth/* endpoints."""
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import VALID_GSTIN, VALID_PASSWORD, unique_email, valid_register_payload


class TestRegister:
    async def test_register_valid_returns_tokens(self, client: AsyncClient):
        payload = valid_register_payload()
        r = await client.post("/auth/register", json=payload)
        assert r.status_code in (200, 201)
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email_rejected(self, client: AsyncClient):
        payload = valid_register_payload()
        await client.post("/auth/register", json=payload)
        r2 = await client.post("/auth/register", json=payload)
        assert r2.status_code in (400, 409, 422)

    async def test_register_weak_password_rejected(self, client: AsyncClient):
        payload = valid_register_payload(password="weak", confirm_password="weak")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_password_mismatch_rejected(self, client: AsyncClient):
        payload = valid_register_payload(confirm_password="Different@1234!")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_invalid_gstin_rejected(self, client: AsyncClient):
        payload = valid_register_payload(gstin="INVALID_GSTIN")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_no_platform_rejected(self, client: AsyncClient):
        payload = valid_register_payload(active_platforms=[])
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_invalid_email_rejected(self, client: AsyncClient):
        payload = valid_register_payload(email="not-an-email")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_short_phone_rejected(self, client: AsyncClient):
        payload = valid_register_payload(phone="123")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_missing_name_rejected(self, client: AsyncClient):
        payload = valid_register_payload()
        del payload["name"]
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_access_token_is_valid_jwt(self, client: AsyncClient):
        from app.core.security import decode_access_token
        payload = valid_register_payload()
        r = await client.post("/auth/register", json=payload)
        assert r.status_code in (200, 201)
        token = r.json()["access_token"]
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["type"] == "access"


class TestLogin:
    async def test_login_valid_returns_tokens(self, client: AsyncClient):
        payload = valid_register_payload()
        await client.post("/auth/register", json=payload)
        r = await client.post("/auth/login", json={
            "email": payload["email"],
            "password": payload["password"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password_rejected(self, client: AsyncClient):
        payload = valid_register_payload()
        await client.post("/auth/register", json=payload)
        r = await client.post("/auth/login", json={
            "email": payload["email"],
            "password": "WrongPass@999!",
        })
        assert r.status_code in (400, 401, 403)

    async def test_login_unknown_email_rejected(self, client: AsyncClient):
        r = await client.post("/auth/login", json={
            "email": f"nobody_{uuid.uuid4().hex}@nowhere.dev",
            "password": VALID_PASSWORD,
        })
        assert r.status_code in (400, 401, 403, 404)

    async def test_login_missing_fields_rejected(self, client: AsyncClient):
        r = await client.post("/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        r = await client.get("/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "email" in data

    async def test_get_me_unauthenticated_rejected(self, client: AsyncClient):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_get_me_invalid_token_rejected(self, client: AsyncClient):
        r = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


class TestRefreshToken:
    async def test_refresh_returns_new_tokens(self, client: AsyncClient):
        payload = valid_register_payload()
        reg = await client.post("/auth/register", json=payload)
        assert reg.status_code in (200, 201)
        refresh_token = reg.json()["refresh_token"]
        r = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data

    async def test_refresh_invalid_token_rejected(self, client: AsyncClient):
        r = await client.post("/auth/refresh", json={"refresh_token": "bogus-token"})
        assert r.status_code in (400, 401, 403)


class TestLogout:
    async def test_logout_clears_session(self, client: AsyncClient):
        payload = valid_register_payload()
        reg = await client.post("/auth/register", json=payload)
        assert reg.status_code in (200, 201)
        tokens = reg.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        r = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers)
        assert r.status_code in (200, 204)

    async def test_logout_without_token_still_ok(self, client: AsyncClient, auth_headers: dict):
        r = await client.post("/auth/logout", json={}, headers=auth_headers)
        assert r.status_code in (200, 204)


class TestForgotPassword:
    async def test_forgot_password_known_email_returns_200(self, client: AsyncClient):
        payload = valid_register_payload()
        await client.post("/auth/register", json=payload)
        r = await client.post("/auth/forgot-password", json={"email": payload["email"]})
        assert r.status_code == 200

    async def test_forgot_password_unknown_email_still_200(self, client: AsyncClient):
        r = await client.post("/auth/forgot-password", json={"email": "nobody@nowhere.dev"})
        assert r.status_code == 200  # anti-enumeration: always 200

    async def test_forgot_password_invalid_email_422(self, client: AsyncClient):
        r = await client.post("/auth/forgot-password", json={"email": "not-email"})
        assert r.status_code == 422
