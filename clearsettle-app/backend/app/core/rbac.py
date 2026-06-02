"""
Role-Based Access Control for ClearSettle.

Architecture:
  - Static PERMISSIONS dict: legacy fallback / mock-data mode
  - DB-backed: roles → permissions loaded at startup into _perm_cache
  - Tenant-aware: permission checks can be scoped to company_id + branch_id
  - User-level overrides: user_permissions table overrides role grants

Permission naming:
  Legacy format:    "module:action"  (e.g. "dashboard:read")
  Enterprise format: "module.action" (e.g. "dashboard.view")
  Both are supported; the cache unifies them.

Audit events go to the "clearsettle.audit" logger as structured JSON.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.core.deps import get_current_user, require_db_user

logger = logging.getLogger("clearsettle.audit")

# ── Static fallback ────────────────────────────────────────────────────────────
# Used when DB is unavailable / mock mode. Maps permission → allowed roles.
PERMISSIONS: dict[str, frozenset[str]] = {
    "dashboard:read":             frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "gst_consultant", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "dashboard.view":             frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "gst_consultant", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "analytics:read":             frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant"}),
    "settlements:read":           frozenset({"admin", "member", "finance", "ca", "viewer", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "settlements.view":           frozenset({"admin", "member", "finance", "ca", "viewer", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "settlements:dispute":        frozenset({"admin", "member", "seller", "company_admin", "finance_manager"}),
    "settlements.export":         frozenset({"admin", "member", "seller", "company_admin", "business_owner", "finance_manager", "reconciliation_analyst", "ca_admin"}),
    "reconciliation:read":        frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "branch_manager", "branch_accountant"}),
    "reconciliation.view":        frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "branch_manager", "branch_accountant"}),
    "reconciliation:run":         frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "reconciliation_analyst", "branch_manager"}),
    "reconciliation.run":         frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "reconciliation_analyst", "branch_manager"}),
    "reconciliation:resolve":     frozenset({"admin", "member", "seller", "company_admin", "finance_manager"}),
    "reconciliation.export":      frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "reconciliation_analyst", "ca_admin"}),
    "reconciliation:rules:read":  frozenset({"admin", "member", "finance", "ca", "seller", "company_admin"}),
    "reconciliation:rules:write": frozenset({"admin", "seller", "company_admin"}),
    "reconciliation:seed":        frozenset({"admin"}),
    "bank_reconciliation.view":   frozenset({"admin", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "branch_manager", "branch_accountant"}),
    "bank_reconciliation.run":    frozenset({"admin", "company_admin", "finance_manager", "reconciliation_analyst", "ca_admin"}),
    "platforms:read":             frozenset({"admin", "member", "seller", "company_admin", "business_owner", "finance_manager"}),
    "platforms:write":            frozenset({"admin", "seller", "company_admin", "business_owner"}),
    "marketplace.view":           frozenset({"admin", "member", "seller", "company_admin", "business_owner", "finance_manager"}),
    "marketplace.connect":        frozenset({"admin", "seller", "company_admin", "business_owner"}),
    "marketplace.disconnect":     frozenset({"admin", "seller", "company_admin", "business_owner"}),
    "marketplace.sync":           frozenset({"admin", "seller", "company_admin", "business_owner"}),
    "sync:read":                  frozenset({"admin", "member", "seller", "company_admin"}),
    "sync:trigger":               frozenset({"admin", "member", "seller", "company_admin"}),
    "reports:read":               frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "reports.view":               frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer", "branch_manager", "branch_accountant", "branch_viewer"}),
    "reports.upload":             frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "accountant", "branch_manager", "branch_accountant"}),
    "reports.delete":             frozenset({"admin", "company_admin"}),
    "reports.download":           frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "ca_reviewer", "branch_manager", "branch_accountant"}),
    "disputes:read":              frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "auditor", "ca_admin", "branch_manager", "branch_accountant", "branch_viewer"}),
    "disputes.view":              frozenset({"admin", "member", "finance", "ca", "seller", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin", "branch_manager", "branch_accountant", "branch_viewer"}),
    "disputes:write":             frozenset({"admin", "member", "seller", "company_admin", "finance_manager"}),
    "disputes.create":            frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "branch_manager"}),
    "disputes.update":            frozenset({"admin", "member", "seller", "company_admin", "finance_manager", "branch_manager"}),
    "disputes.close":             frozenset({"admin", "company_admin", "finance_manager"}),
    "admin:users":                frozenset({"admin", "superadmin", "company_admin"}),
    "admin:roles":                frozenset({"admin", "superadmin", "company_admin"}),
    "users.view":                 frozenset({"admin", "superadmin", "company_admin", "business_owner", "auditor", "ca_admin", "branch_manager"}),
    "users.create":               frozenset({"admin", "superadmin", "company_admin"}),
    "users.update":               frozenset({"admin", "superadmin", "company_admin"}),
    "users.delete":               frozenset({"admin", "superadmin", "company_admin"}),
    "roles.assign":               frozenset({"admin", "superadmin", "company_admin"}),
    "rules:read":                 frozenset({"admin", "member", "finance", "ca", "seller", "company_admin"}),
    "rules:write":                frozenset({"admin", "company_admin"}),
    "rules:test":                 frozenset({"admin", "member", "seller", "company_admin"}),
    "onboarding:read":            frozenset({"admin", "member", "seller", "company_admin"}),
    "onboarding:write":           frozenset({"admin", "member", "seller", "company_admin"}),
    "gst.view":                   frozenset({"admin", "company_admin", "business_owner", "finance_manager", "accountant", "gst_consultant", "auditor", "ca_admin", "ca_reviewer", "branch_manager", "branch_accountant"}),
    "gst.file":                   frozenset({"admin", "company_admin", "finance_manager", "gst_consultant", "ca_admin"}),
    "gst.export":                 frozenset({"admin", "company_admin", "finance_manager", "gst_consultant", "ca_admin"}),
    "gstr1.view":                 frozenset({"admin", "company_admin", "business_owner", "finance_manager", "accountant", "gst_consultant", "auditor", "ca_admin", "ca_reviewer"}),
    "gstr1.file":                 frozenset({"admin", "company_admin", "finance_manager", "gst_consultant", "ca_admin"}),
    "gstr3b.view":                frozenset({"admin", "company_admin", "business_owner", "finance_manager", "accountant", "gst_consultant", "auditor", "ca_admin", "ca_reviewer"}),
    "gstr3b.file":                frozenset({"admin", "company_admin", "finance_manager", "gst_consultant", "ca_admin"}),
    "ai.view":                    frozenset({"admin", "company_admin", "business_owner", "finance_manager", "accountant", "reconciliation_analyst", "auditor", "ca_admin"}),
    "ai.generate":                frozenset({"admin", "company_admin", "business_owner", "finance_manager"}),
    "audit.view":                 frozenset({"admin", "superadmin", "company_admin", "business_owner", "auditor", "ca_admin"}),
    "subscription.view":          frozenset({"admin", "company_admin", "business_owner"}),
    "subscription.manage":        frozenset({"admin", "company_admin", "business_owner"}),
    "settings.update":            frozenset({"admin", "company_admin", "business_owner"}),
    "notifications.manage":       frozenset({"admin", "company_admin"}),
}

# ── In-memory DB cache ────────────────────────────────────────────────────────
_perm_cache: dict[str, frozenset[str]] | None = None


def _active_permissions() -> dict[str, frozenset[str]]:
    return _perm_cache if _perm_cache is not None else PERMISSIONS


# ── DB loading ────────────────────────────────────────────────────────────────

async def load_rbac_from_db(session) -> None:
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
            "RBAC cache loaded: %d permissions, %d roles",
            len(_perm_cache),
            len({r for roles in _perm_cache.values() for r in roles}),
        )
    except Exception as exc:
        logger.warning("RBAC DB load failed — using static fallback: %s", exc)
        _perm_cache = None


async def reload_rbac_cache(session) -> dict:
    await load_rbac_from_db(session)
    cache = _perm_cache or PERMISSIONS
    return {
        "source":      "database" if _perm_cache is not None else "static_fallback",
        "permissions": len(cache),
        "roles":       sorted({r for roles in cache.values() for r in roles}),
    }


# ── User effective permissions (DB-aware) ─────────────────────────────────────

async def get_user_effective_permissions(
    user, session, company_id: str | None = None
) -> set[str]:
    """
    Return the full set of permission names for a user.
    Considers: role-based permissions + direct user_permissions overrides.
    When company_id is given, only returns permissions scoped to that tenant.
    """
    role = get_user_role(user)
    base_perms = get_role_permissions(role)

    try:
        from sqlalchemy import select, and_
        from app.db.models.rbac import UserPermission, Permission, UserRole, RolePermission

        uid = str(getattr(user, "id", ""))

        # Fetch role-based perms from user_roles (multi-role support)
        stmt = (
            select(Permission.name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == uid)
        )
        if company_id:
            stmt = stmt.where(
                (UserRole.company_id == company_id) | (UserRole.company_id.is_(None))
            )
        result = await session.execute(stmt)
        role_perms = {row[0] for row in result.all()}

        # Fetch direct overrides
        override_stmt = (
            select(Permission.name, UserPermission.granted)
            .join(Permission, Permission.id == UserPermission.permission_id)
            .where(UserPermission.user_id == uid)
        )
        if company_id:
            override_stmt = override_stmt.where(
                (UserPermission.company_id == company_id) | (UserPermission.company_id.is_(None))
            )
        override_result = await session.execute(override_stmt)
        overrides = {row[0]: row[1] for row in override_result.all()}

        effective = (base_perms | role_perms)
        for perm_name, granted in overrides.items():
            if granted:
                effective.add(perm_name)
            else:
                effective.discard(perm_name)
        return effective

    except Exception:
        return base_perms


# ── Core helpers ──────────────────────────────────────────────────────────────

def get_user_role(user) -> str:
    if isinstance(user, dict):
        return user.get("role", "admin")
    return getattr(user, "role", "admin") or "admin"


def check_permission(user, permission: str) -> bool:
    role = get_user_role(user)
    return role in _active_permissions().get(permission, frozenset())


def _check_permission(user, permission: str) -> None:
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
                "required_permission": permission,
                "required_roles": sorted(allowed),
                "your_role": role,
            },
        )


def audit_log(
    user,
    action: str,
    *,
    resource_id: Any = None,
    company_id:  Any = None,
    branch_id:   Any = None,
    ip_address:  str | None = None,
    extra: dict | None = None,
) -> None:
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
        "branch_id":   str(branch_id)   if branch_id   is not None else None,
        "ip_address":  ip_address,
    }
    if extra:
        payload.update(extra)
    logger.info(json.dumps(payload))


async def write_audit_db(
    session,
    *,
    user_id: str | None,
    company_id: str | None,
    action: str,
    resource: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Persist an audit log entry to the database."""
    try:
        import uuid as _uuid
        from app.db.models.audit_log_entry import AuditLogEntry
        entry = AuditLogEntry(
            id=_uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            log_metadata=metadata or {},
        )
        session.add(entry)
        await session.commit()
    except Exception as exc:
        logger.warning("Could not write audit log to DB: %s", exc)


# ── FastAPI dependency factories ──────────────────────────────────────────────

def require_permission(permission: str):
    """
    Authenticate (DB or mock) and enforce the given permission.

    Usage::
        @router.post("/foo")
        async def foo(user=Depends(require_permission("reports.upload"))):
            ...
    """
    async def _dep(user=Depends(get_current_user)):
        _check_permission(user, permission)
        return user
    return _dep


def require_db_permission(permission: str):
    """Require a live-DB user and enforce the given permission. No mock fallback."""
    async def _dep(user=Depends(require_db_user)):
        _check_permission(user, permission)
        return user
    return _dep


# ── Role → permissions helper ─────────────────────────────────────────────────

def get_role_permissions(role: str) -> set[str]:
    src = _active_permissions()
    return {perm for perm, roles in src.items() if role in roles}
