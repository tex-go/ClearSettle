"""
RBAC Login Integration Tests
Tests that every role can:
  - Register with a valid role
  - Login and receive tokens
  - Fetch /auth/me and see the correct role
  - Fetch /auth/permissions and receive a non-empty permission list
  - Be rejected on wrong password (401)
"""
import pytest
from httpx import AsyncClient

from tests.conftest import VALID_PASSWORD, unique_email, valid_register_payload_for_role

# All roles that can self-register via POST /auth/register
SELF_REGISTER_ROLES = [
    "company_admin",
    "business_owner",
    "finance_manager",
    "accountant",
    "reconciliation_analyst",
    "gst_consultant",
    "auditor",
    "ca_admin",
    "ca_reviewer",
    "ca_staff",
    "ca_viewer",
    "branch_manager",
    "branch_accountant",
    "branch_viewer",
]

# System roles created directly (superadmin/admin) — test login only, not register
SYSTEM_ROLES = ["admin", "superadmin"]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, role: str) -> tuple[str, str, str]:
    """Register a fresh user with the given role, login, return (email, token, role)."""
    email = unique_email()
    payload = valid_register_payload_for_role(role, email=email)
    reg = await client.post("/auth/register", json=payload)
    assert reg.status_code in (200, 201), f"Register failed for role={role}: {reg.text}"

    login_r = await client.post("/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert login_r.status_code == 200, f"Login failed for role={role}: {login_r.text}"

    token = login_r.json()["access_token"]
    return email, token, role


# ── Registration tests ────────────────────────────────────────────────────────

class TestRbacRegistration:
    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_register_with_role_returns_201(self, client: AsyncClient, role: str):
        payload = valid_register_payload_for_role(role)
        r = await client.post("/auth/register", json=payload)
        assert r.status_code in (200, 201), f"role={role}: {r.text}"

    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_register_with_role_returns_tokens(self, client: AsyncClient, role: str):
        payload = valid_register_payload_for_role(role)
        r = await client.post("/auth/register", json=payload)
        assert r.status_code in (200, 201)
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_register_invalid_role_rejected(self, client: AsyncClient):
        payload = valid_register_payload_for_role("company_admin", role_override="hacker_role")
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 422

    async def test_register_duplicate_email_rejected(self, client: AsyncClient):
        email = unique_email()
        payload = valid_register_payload_for_role("company_admin", email=email)
        await client.post("/auth/register", json=payload)
        r2 = await client.post("/auth/register", json=payload)
        assert r2.status_code in (400, 409)


# ── Login tests (all roles) ───────────────────────────────────────────────────

class TestRbacLogin:
    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_login_success_for_role(self, client: AsyncClient, role: str):
        email, token, _ = await register_and_login(client, role)
        assert token, f"No token for role={role}"

    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_login_wrong_password_returns_401(self, client: AsyncClient, role: str):
        email = unique_email()
        payload = valid_register_payload_for_role(role, email=email)
        await client.post("/auth/register", json=payload)

        r = await client.post("/auth/login", json={"email": email, "password": "WrongPass@99"})
        assert r.status_code == 401, f"Expected 401 for wrong password, role={role}"

    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient):
        r = await client.post("/auth/login", json={
            "email": "ghost_user_xyz@clearsettle-test.dev",
            "password": VALID_PASSWORD,
        })
        assert r.status_code == 401

    async def test_login_missing_email_returns_422(self, client: AsyncClient):
        r = await client.post("/auth/login", json={"password": VALID_PASSWORD})
        assert r.status_code == 422

    async def test_login_missing_password_returns_422(self, client: AsyncClient):
        r = await client.post("/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422


# ── /auth/me role verification ────────────────────────────────────────────────

class TestRbacMeEndpoint:
    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_me_returns_correct_role(self, client: AsyncClient, role: str):
        _, token, _ = await register_and_login(client, role)
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"GET /auth/me failed for role={role}: {r.text}"
        body = r.json()
        assert body.get("role") == role, (
            f"Expected role={role}, got role={body.get('role')}"
        )

    async def test_me_unauthenticated_returns_401(self, client: AsyncClient):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_me_invalid_token_returns_401(self, client: AsyncClient):
        r = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert r.status_code == 401


# ── /auth/permissions role verification ──────────────────────────────────────

class TestRbacPermissionsEndpoint:
    @pytest.mark.parametrize("role", SELF_REGISTER_ROLES)
    async def test_permissions_non_empty_for_role(self, client: AsyncClient, role: str):
        _, token, _ = await register_and_login(client, role)
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"GET /auth/permissions failed for role={role}: {r.text}"
        perms = r.json()
        assert isinstance(perms, list), f"Expected list, got {type(perms)}"
        assert len(perms) > 0, f"Empty permissions for role={role}"

    async def test_permissions_unauthenticated_returns_401(self, client: AsyncClient):
        r = await client.get("/auth/permissions")
        assert r.status_code == 401

    # ── Role-specific permission checks ──────────────────────────────────────

    async def test_auditor_has_only_view_permissions(self, client: AsyncClient):
        _, token, _ = await register_and_login(client, "auditor")
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        perms: list[str] = r.json()
        write_actions = [p for p in perms if any(
            p.endswith(a) for a in [".upload", ".create", ".update", ".delete", ".run", ".connect"]
        )]
        assert not write_actions, f"Auditor should have no write permissions, got: {write_actions}"

    async def test_finance_manager_can_upload(self, client: AsyncClient):
        _, token, _ = await register_and_login(client, "finance_manager")
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        perms: list[str] = r.json()
        assert any("upload" in p for p in perms), "finance_manager should have upload permission"

    async def test_company_admin_has_user_management(self, client: AsyncClient):
        _, token, _ = await register_and_login(client, "company_admin")
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        perms: list[str] = r.json()
        assert any("users" in p for p in perms), "company_admin should have users permission"

    async def test_branch_viewer_cannot_upload(self, client: AsyncClient):
        _, token, _ = await register_and_login(client, "branch_viewer")
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        perms: list[str] = r.json()
        assert not any("upload" in p for p in perms), "branch_viewer must not have upload permission"

    async def test_gst_consultant_has_gst_permissions(self, client: AsyncClient):
        _, token, _ = await register_and_login(client, "gst_consultant")
        r = await client.get("/auth/permissions", headers={"Authorization": f"Bearer {token}"})
        perms: list[str] = r.json()
        assert any("gst" in p for p in perms), "gst_consultant should have gst permissions"


# ── Public endpoints ──────────────────────────────────────────────────────────

class TestPublicAuthEndpoints:
    async def test_get_roles_returns_list(self, client: AsyncClient):
        r = await client.get("/auth/roles")
        assert r.status_code == 200
        body = r.json()
        assert "roles" in body
        assert isinstance(body["roles"], list)
        assert len(body["roles"]) > 0

    async def test_check_email_available(self, client: AsyncClient):
        r = await client.post("/auth/check-email", json={"email": f"brand.new.{unique_email()}"})
        assert r.status_code == 200
        assert r.json().get("available") is True

    async def test_check_email_taken(self, client: AsyncClient):
        email = unique_email()
        payload = valid_register_payload_for_role("company_admin", email=email)
        await client.post("/auth/register", json=payload)

        r = await client.post("/auth/check-email", json={"email": email})
        assert r.status_code == 200
        assert r.json().get("available") is False
