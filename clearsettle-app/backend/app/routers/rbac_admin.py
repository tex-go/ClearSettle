"""
RBAC Administration Router
GET  /admin/rbac/roles                  — list all roles
POST /admin/rbac/roles                  — create custom role
GET  /admin/rbac/permissions            — list all permissions
POST /admin/rbac/roles/{id}/permissions — assign permission to role
GET  /admin/rbac/users/{user_id}/permissions — user effective permissions
POST /admin/rbac/users/{user_id}/roles  — assign role to user
DELETE /admin/rbac/users/{user_id}/roles/{role_id} — remove role from user
GET  /admin/rbac/branches               — list branches for current tenant
POST /admin/rbac/branches               — create branch
GET  /admin/rbac/audit-logs             — paginated audit log
GET  /admin/rbac/reload-cache           — hot-reload permission cache (superadmin only)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rbac import (
    require_permission,
    require_db_permission,
    reload_rbac_cache,
    get_user_effective_permissions,
    audit_log,
    write_audit_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/rbac", tags=["RBAC Admin"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class RoleOut(BaseModel):
    id: int
    name: str
    scope: str
    description: str | None
    is_active: bool
    is_custom: bool
    company_id: str | None

    class Config:
        from_attributes = True


class PermissionOut(BaseModel):
    id: int
    name: str
    module: str | None
    action: str | None
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True


class CreateRoleRequest(BaseModel):
    name: str
    description: str | None = None
    scope: str = "tenant"
    permissions: list[str] = []


class AssignPermissionRequest(BaseModel):
    permission_name: str


class AssignRoleRequest(BaseModel):
    role_name: str
    company_id: str | None = None
    branch_id: str | None = None


class BranchCreateRequest(BaseModel):
    name: str
    city: str | None = None
    state: str | None = None
    address: str | None = None
    gstin: str | None = None


class BranchOut(BaseModel):
    id: str
    company_id: str
    name: str
    city: str | None
    state: str | None
    is_active: bool

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_company_id(user) -> str | None:
    if isinstance(user, dict):
        return None
    companies = getattr(user, "companies", [])
    if companies:
        return str(companies[0].id)
    return None


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import Role
    result = await db.execute(select(Role).where(Role.is_active.is_(True)).order_by(Role.name))
    roles = result.scalars().all()
    return [
        RoleOut(
            id=r.id, name=r.name, scope=r.scope, description=r.description,
            is_active=r.is_active, is_custom=r.is_custom,
            company_id=str(r.company_id) if r.company_id else None,
        )
        for r in roles
    ]


@router.post("/roles", response_model=RoleOut, status_code=201)
async def create_custom_role(
    body: CreateRoleRequest,
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import Role, Permission, RolePermission
    company_id = _get_company_id(user)

    # Check for duplicate name within the tenant
    existing = await db.execute(
        select(Role).where(Role.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Role '{body.name}' already exists.")

    role = Role(
        name=body.name,
        description=body.description,
        scope=body.scope,
        is_custom=True,
        company_id=uuid.UUID(company_id) if company_id else None,
    )
    db.add(role)
    await db.flush()

    # Assign permissions
    for perm_name in body.permissions:
        perm_result = await db.execute(select(Permission).where(Permission.name == perm_name))
        perm = perm_result.scalar_one_or_none()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.commit()
    await db.refresh(role)
    audit_log(user, "role.create", extra={"role_name": body.name})
    return RoleOut(
        id=role.id, name=role.name, scope=role.scope, description=role.description,
        is_active=role.is_active, is_custom=role.is_custom,
        company_id=str(role.company_id) if role.company_id else None,
    )


@router.post("/roles/{role_id}/permissions", status_code=200)
async def assign_permission_to_role(
    role_id: int,
    body: AssignPermissionRequest,
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import Role, Permission, RolePermission
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(404, "Role not found")

    perm_result = await db.execute(select(Permission).where(Permission.name == body.permission_name))
    perm = perm_result.scalar_one_or_none()
    if not perm:
        raise HTTPException(404, f"Permission '{body.permission_name}' not found")

    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        return {"message": "Permission already assigned"}

    audit_log(user, "role.permission_assign", extra={"role": role.name, "permission": body.permission_name})
    return {"message": f"Permission '{body.permission_name}' assigned to role '{role.name}'"}


# ── Permissions ────────────────────────────────────────────────────────────────

@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    module: str | None = Query(None),
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import Permission
    stmt = select(Permission).where(Permission.is_active.is_(True))
    if module:
        stmt = stmt.where(Permission.module == module)
    stmt = stmt.order_by(Permission.module, Permission.action)
    result = await db.execute(stmt)
    perms = result.scalars().all()
    return [
        PermissionOut(
            id=p.id, name=p.name, module=p.module, action=p.action,
            description=p.description, is_active=p.is_active,
        )
        for p in perms
    ]


# ── User Role Assignment ───────────────────────────────────────────────────────

@router.post("/users/{user_id}/roles", status_code=201)
async def assign_role_to_user(
    user_id: str,
    body: AssignRoleRequest,
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import Role, UserRole
    from app.db.models.user import User as UserModel

    target_result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(user_id)))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    role_result = await db.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(404, f"Role '{body.role_name}' not found")

    company_id = uuid.UUID(body.company_id) if body.company_id else None
    branch_id  = uuid.UUID(body.branch_id)  if body.branch_id  else None

    ur = UserRole(
        user_id=uuid.UUID(user_id),
        role_id=role.id,
        company_id=company_id,
        branch_id=branch_id,
        granted_by=getattr(user, "id", None),
    )
    db.add(ur)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        return {"message": "Role already assigned"}

    audit_log(user, "user.role_assign", resource_id=user_id,
              company_id=body.company_id,
              extra={"role": body.role_name})
    return {"message": f"Role '{body.role_name}' assigned to user '{user_id}'"}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=200)
async def remove_role_from_user(
    user_id: str,
    role_id: int,
    company_id: str | None = Query(None),
    user=Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.rbac import UserRole
    from sqlalchemy import delete

    stmt = delete(UserRole).where(
        UserRole.user_id == uuid.UUID(user_id),
        UserRole.role_id == role_id,
    )
    if company_id:
        stmt = stmt.where(UserRole.company_id == uuid.UUID(company_id))
    await db.execute(stmt)
    await db.commit()
    audit_log(user, "user.role_revoke", resource_id=user_id, extra={"role_id": role_id})
    return {"message": "Role removed"}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    company_id: str | None = Query(None),
    user=Depends(require_permission("users.view")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.user import User as UserModel
    target_result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(user_id)))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    effective = await get_user_effective_permissions(target, db, company_id=company_id)
    return {
        "user_id": user_id,
        "company_id": company_id,
        "role": getattr(target, "role", None),
        "permissions": sorted(effective),
    }


# ── Branches ───────────────────────────────────────────────────────────────────

@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    user=Depends(require_permission("settings.update")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.branch import Branch
    company_id = _get_company_id(user)
    if not company_id:
        return []
    result = await db.execute(
        select(Branch)
        .where(Branch.company_id == uuid.UUID(company_id), Branch.is_active.is_(True))
        .order_by(Branch.name)
    )
    return [
        BranchOut(
            id=str(b.id), company_id=str(b.company_id), name=b.name,
            city=b.city, state=b.state, is_active=b.is_active,
        )
        for b in result.scalars().all()
    ]


@router.post("/branches", response_model=BranchOut, status_code=201)
async def create_branch(
    body: BranchCreateRequest,
    user=Depends(require_permission("settings.update")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.branch import Branch
    company_id = _get_company_id(user)
    if not company_id:
        raise HTTPException(400, "No company associated with your account")

    branch = Branch(
        id=uuid.uuid4(),
        company_id=uuid.UUID(company_id),
        name=body.name,
        city=body.city,
        state=body.state,
        address=body.address,
        gstin=body.gstin,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    audit_log(user, "branch.create", company_id=company_id, extra={"branch_name": body.name})
    return BranchOut(
        id=str(branch.id), company_id=str(branch.company_id), name=branch.name,
        city=branch.city, state=branch.state, is_active=branch.is_active,
    )


# ── Audit Logs ─────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action_filter: str | None = Query(None),
    user=Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.audit_log_entry import AuditLogEntry
    company_id = _get_company_id(user)

    stmt = select(AuditLogEntry)
    if company_id:
        stmt = stmt.where(AuditLogEntry.company_id == uuid.UUID(company_id))
    if action_filter:
        stmt = stmt.where(AuditLogEntry.action.ilike(f"%{action_filter}%"))
    stmt = stmt.order_by(AuditLogEntry.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "entries": [
            {
                "id": str(e.id),
                "user_id": str(e.user_id) if e.user_id else None,
                "company_id": str(e.company_id) if e.company_id else None,
                "action": e.action,
                "resource": e.resource,
                "resource_id": e.resource_id,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


# ── Cache Reload ───────────────────────────────────────────────────────────────

@router.post("/reload-cache")
async def reload_permission_cache(
    user=Depends(require_permission("admin:roles")),
    db: AsyncSession = Depends(get_db),
):
    stats = await reload_rbac_cache(db)
    audit_log(user, "rbac.cache_reload")
    return stats
