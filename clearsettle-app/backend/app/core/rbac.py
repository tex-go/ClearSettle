"""
Role-Based Access Control for ClearSettle.

Permissions live in the database (roles / permissions / role_permissions tables).
On startup, `load_rbac_from_db()` populates an in-memory cache so every request
is a pure dict lookup — no per-request DB round-trip.

The static PERMISSIONS dict below is the **fallback** used in mock-data mode (no DB).
Call `reload_rbac_cache(session)` after any runtime permission change.

Audit events are emitted to the "clearsettle.audit" logger as structured JSON.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user, require_db_user

logger = logging.getLogger("clearsettle.audit")

# ── Static fallback (used when DB is unavailable / mock mode) ─────────────────

PERMISSIONS: dict[str, frozenset[str]] = {
    "dashboard:read":             frozenset({"admin", "member", "finance", "ca", "seller"}),
    "analytics:read":             frozenset({"admin", "member", "finance", "ca", "seller"}),
    "settlements:read":           frozenset({"admin", "member", "finance", "ca", "viewer", "seller"}),
    "settlements:dispute":        frozenset({"admin", "member", "seller"}),
    "reconciliation:read":        frozenset({"admin", "member", "finance", "ca", "seller"}),
    "reconciliation:run":         frozenset({"admin", "member", "seller"}),
    "reconciliation:resolve":     frozenset({"admin", "member", "seller"}),
    "reconciliation:rules:read":  frozenset({"admin", "member", "finance", "ca", "seller"}),
    "reconciliation:rules:write": frozenset({"admin", "seller"}),
    "reconciliation:seed":        frozenset({"admin"}),
    "platforms:read":             frozenset({"admin", "member", "seller"}),
    "platforms:write":            frozenset({"admin", "seller"}),
    "sync:read":                  frozenset({"admin", "member", "seller"}),
    "sync:trigger":               frozenset({"admin", "member", "seller"}),
    "reports:read":               frozenset({"admin", "member", "finance", "ca", "seller"}),
    "disputes:read":              frozenset({"admin", "member", "finance", "ca", "seller"}),
    "disputes:write":             frozenset({"admin", "member", "seller"}),
    "admin:users":                frozenset({"admin", "superadmin"}),
    "admin:roles":                frozenset({"admin", "superadmin"}),
    "rules:read":                 frozenset({"admin", "member", "finance", "ca", "seller"}),
    "rules:write":                frozenset({"admin"}),
    "rules:test":                 frozenset({"admin", "member", "seller"}),
    "onboarding:read":            frozenset({"admin", "member", "seller"}),
    "onboarding:write":           frozenset({"admin", "member", "seller"}),
}

# ── In-memory DB cache ────────────────────────────────────────────────────────
# Populated at startup by load_rbac_from_db(); None means "not yet loaded".
# Structure mirrors PERMISSIONS: permission_name → frozenset of role names.
_perm_cache: dict[str, frozenset[str]] | None = None


def _active_permissions() -> dict[str, frozenset[str]]:
    """Return the DB cache when available, else the static fallback."""
    return _perm_cache if _perm_cache is not None else PERMISSIONS


# ── DB loading ────────────────────────────────────────────────────────────────

async def load_rbac_from_db(session) -> None:
    """
    Load all active role→permission mappings from the DB into the in-memory cache.
    Called once at startup; also callable via the admin reload endpoint.
    """
    global _perm_cache
    try:
        from sqlalchemy import select
        from app.db.models.rbac import Role, Permission, RolePermission

        stmt = (
            select(Permission.name, Role.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Role.is_active.is_(True))
        )
        result = await session.execute(stmt)
        rows = result.all()

        cache: dict[str, set[str]] = {}
        for perm_name, role_name in rows:
            cache.setdefault(perm_name, set()).add(role_name)
        _perm_cache = {k: frozenset(v) for k, v in cache.items()}
        logger.info(
            "RBAC cache loaded from DB: %d permissions across %d roles",
            len(_perm_cache),
            len({r for roles in _perm_cache.values() for r in roles}),
        )
    except Exception as exc:
        logger.warning("RBAC DB load failed — using static fallback: %s", exc)
        _perm_cache = None


async def reload_rbac_cache(session) -> dict:
    """Reload the permission cache and return stats (for admin endpoint)."""
    await load_rbac_from_db(session)
    cache = _perm_cache or PERMISSIONS
    return {
        "source":      "database" if _perm_cache is not None else "static_fallback",
        "permissions": len(cache),
        "roles":       sorted({r for roles in cache.values() for r in roles}),
    }


# ── Core helpers ──────────────────────────────────────────────────────────────

def get_user_role(user) -> str:
    """Return the role string for an ORM User or a mock dict."""
    if isinstance(user, dict):
        return user.get("role", "admin")
    return getattr(user, "role", "admin") or "admin"


def check_permission(user, permission: str) -> bool:
    """Return True if the user's role grants the given permission."""
    role = get_user_role(user)
    return role in _active_permissions().get(permission, frozenset())


def _check_permission(user, permission: str) -> None:
    """Raise HTTP 403 with a structured body if the user lacks the permission."""
    role    = get_user_role(user)
    allowed = _active_permissions().get(permission, frozenset())
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": (
                    f"Permission denied: '{permission}' requires one of: "
                    f"{sorted(allowed)}"
                ),
                "required_roles": sorted(allowed),
                "your_role":      role,
            },
        )


def audit_log(
    user,
    action: str,
    *,
    resource_id: Any = None,
    company_id:  Any = None,
    extra: dict | None = None,
) -> None:
    """Emit a structured audit event to the clearsettle.audit logger."""
    if isinstance(user, dict):
        user_id = str(user.get("id", "demo"))
    else:
        user_id = str(getattr(user, "id", "unknown"))

    payload: dict[str, Any] = {
        "event":       "rbac_action",
        "user_id":     user_id,
        "role":        get_user_role(user),
        "action":      action,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "company_id":  str(company_id)  if company_id  is not None else None,
    }
    if extra:
        payload.update(extra)
    logger.info(json.dumps(payload))


# ── FastAPI dependency factories ──────────────────────────────────────────────

def require_permission(permission: str):
    """
    Authenticate the request (DB or mock) and enforce the given permission.

    Usage::

        @router.post("/foo")
        async def foo(user=Depends(require_permission("settlements:dispute"))):
            ...
    """
    async def _dep(user=Depends(get_current_user)):
        _check_permission(user, permission)
        return user
    return _dep


def require_db_permission(permission: str):
    """
    Require a live-DB user and enforce the given permission. No mock fallback.

    Usage::

        @router.post("/bar")
        async def bar(user=Depends(require_db_permission("reconciliation:run"))):
            ...
    """
    async def _dep(user=Depends(require_db_user)):
        _check_permission(user, permission)
        return user
    return _dep


# ── Role → permissions helper (derived from active source) ───────────────────

def get_role_permissions(role: str) -> set[str]:
    """Return the set of permission names granted to a role."""
    src = _active_permissions()
    return {perm for perm, roles in src.items() if role in roles}
