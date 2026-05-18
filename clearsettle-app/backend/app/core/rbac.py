"""
Role-Based Access Control for ClearSettle.

Permission matrix and FastAPI dependency factories for enforcing authorization.
Audit events are emitted to the "clearsettle.audit" logger as structured JSON.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user, require_db_user

logger = logging.getLogger("clearsettle.audit")

# ── Permission → allowed roles ────────────────────────────────────────────────

PERMISSIONS: dict[str, frozenset[str]] = {
    "dashboard:read":             frozenset({"admin", "member", "finance", "ca"}),
    "analytics:read":             frozenset({"admin", "member", "finance", "ca"}),
    "settlements:read":           frozenset({"admin", "member", "finance", "ca", "viewer"}),
    "settlements:dispute":        frozenset({"admin", "member"}),
    "reconciliation:read":        frozenset({"admin", "member", "finance", "ca"}),
    "reconciliation:run":         frozenset({"admin", "member"}),
    "reconciliation:resolve":     frozenset({"admin", "member"}),
    "reconciliation:rules:read":  frozenset({"admin", "member", "finance", "ca"}),
    "reconciliation:rules:write": frozenset({"admin"}),
    "reconciliation:seed":        frozenset({"admin"}),
    "platforms:read":             frozenset({"admin", "member"}),
    "platforms:write":            frozenset({"admin"}),
    "sync:read":                  frozenset({"admin", "member"}),
    "sync:trigger":               frozenset({"admin", "member"}),
    "reports:read":               frozenset({"admin", "member", "finance", "ca"}),
    "disputes:read":              frozenset({"admin", "member", "finance", "ca"}),
    "disputes:write":             frozenset({"admin", "member"}),
    "admin:users":                frozenset({"admin"}),
    "admin:roles":                frozenset({"admin"}),
    # Rule engine (Session 8)
    "rules:read":                 frozenset({"admin", "member", "finance", "ca"}),
    "rules:write":                frozenset({"admin"}),
    "rules:test":                 frozenset({"admin", "member"}),
    # Onboarding (Session 9)
    "onboarding:read":            frozenset({"admin", "member"}),
    "onboarding:write":           frozenset({"admin", "member"}),
}

# ── Role → permissions (derived from PERMISSIONS) ────────────────────────────

_ALL_ROLES: frozenset[str] = frozenset({"admin", "member", "finance", "ca", "viewer"})

ROLE_PERMISSIONS: dict[str, set[str]] = {role: set() for role in _ALL_ROLES}
for _perm, _roles in PERMISSIONS.items():
    for _role in _roles:
        ROLE_PERMISSIONS[_role].add(_perm)


# ── Core helpers ──────────────────────────────────────────────────────────────

def get_user_role(user) -> str:
    """Return the role string for an ORM User or a mock dict."""
    if isinstance(user, dict):
        return user.get("role", "admin")
    return getattr(user, "role", "admin") or "admin"


def check_permission(user, permission: str) -> bool:
    """Return True if the user's role grants the given permission."""
    role = get_user_role(user)
    return role in PERMISSIONS.get(permission, frozenset())


def _check_permission(user, permission: str) -> None:
    """Raise HTTP 403 with a structured body if the user lacks the permission."""
    role = get_user_role(user)
    allowed = PERMISSIONS.get(permission, frozenset())
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": (
                    f"Permission denied: '{permission}' requires one of: "
                    f"{sorted(allowed)}"
                ),
                "required_roles": sorted(allowed),
                "your_role": role,
            },
        )


def audit_log(
    user,
    action: str,
    *,
    resource_id: Any = None,
    company_id: Any = None,
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
        "company_id":  str(company_id) if company_id is not None else None,
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
