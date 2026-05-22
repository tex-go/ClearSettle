"""
Auth router.

Endpoints
---------
POST /auth/login         → issue access + refresh tokens
POST /auth/register      → create user + company, issue tokens
POST /auth/refresh       → rotate refresh token, issue new pair
POST /auth/logout        → revoke refresh token
GET  /auth/me            → current user profile
PUT  /auth/me            → update display name
POST /auth/change-password → change password + revoke all refresh tokens

All endpoints fall back to demo-mode (no DB) except register / refresh /
change-password / logout which require a live database.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import DEMO_USER, create_token, verify_password
from app.core.deps import get_current_user, get_db, get_db_optional
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import ChangePasswordRequest, UpdateProfileRequest, UserProfile

router = APIRouter()


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession | None = Depends(get_db_optional)):
    if db is not None:
        from app.services.auth_service import login as svc_login
        return await svc_login(req.email, req.password, db, request=request)

    # ── mock-data / demo mode ─────────────────────────────────────────────────
    if req.email != DEMO_USER["email"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(req.password, DEMO_USER["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_token({"sub": DEMO_USER["email"], "id": DEMO_USER["id"]})
    user = {k: v for k, v in DEMO_USER.items() if k != "hashed_password"}
    return {
        "access_token":  token,
        "refresh_token": "demo-refresh-token",
        "token_type":    "bearer",
        "expires_in":    86400,
        "user":          user,
    }


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import register as svc_register
    return await svc_register(
        email=req.email,
        password=req.password,
        name=req.name,
        company_name=req.company_name,
        db=db,
        phone=req.phone,
        gstin=req.gstin,
        pan=req.pan,
        state=req.state,
        city=req.city,
        pincode=req.pincode,
        address=req.address,
        website=req.website,
        industry=req.industry,
        active_platforms=req.active_platforms,
        monthly_gmv_range=req.monthly_gmv_range,
        bank_name=req.bank_name,
        bank_account_number=req.bank_account_number,
        bank_ifsc=req.bank_ifsc,
        bank_account_name=req.bank_account_name,
        role="seller",
        request=request,
    )


# ── Refresh token ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import refresh_tokens
    return await refresh_tokens(req.refresh_token, db)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: LogoutRequest, db: AsyncSession | None = Depends(get_db_optional)):
    if db is not None and req.refresh_token:
        from app.services.auth_service import logout as svc_logout
        await svc_logout(req.refresh_token, db)


# ── Current user ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def me(current_user=Depends(get_current_user)):
    from app.core.rbac import ROLE_PERMISSIONS, get_user_role
    role = get_user_role(current_user)
    permissions = sorted(ROLE_PERMISSIONS.get(role, set()))

    if isinstance(current_user, dict):
        return UserProfile(
            id=str(current_user.get("id", "")),
            email=current_user["email"],
            name=current_user.get("name"),
            role=role,
            company=current_user.get("company"),
            gstin=current_user.get("gstin"),
            city=current_user.get("city"),
            permissions=permissions,
        )

    company = current_user.companies[0] if current_user.companies else None
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=role,
        phone=getattr(current_user, "phone", None),
        company=company.name if company else None,
        gstin=company.gstin if company else None,
        state=getattr(company, "state", None) if company else None,
        city=company.city if company else None,
        industry=company.industry if company else None,
        active_platforms=getattr(company, "active_platforms", None) or [] if company else [],
        registration_completed=bool(getattr(company, "registration_completed", False)) if company else False,
        permissions=permissions,
    )


@router.get("/permissions")
async def get_permissions(current_user=Depends(get_current_user)):
    """Return all permission strings granted to the current user's role."""
    from app.core.rbac import ROLE_PERMISSIONS, get_user_role
    role = get_user_role(current_user)
    return {"role": role, "permissions": sorted(ROLE_PERMISSIONS.get(role, set()))}


# ── Update profile ────────────────────────────────────────────────────────────

@router.put("/me")
async def update_profile(
    req: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db_optional),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile update requires a database connection")

    if req.name is not None:
        current_user.name = req.name

    if db:
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

    company = current_user.companies[0] if current_user.companies else None
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        company=company.name if company else None,
        gstin=company.gstin if company else None,
        city=company.city if company else None,
    )


# ── Change password ───────────────────────────────────────────────────────────

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    req: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires database connection")

    from app.services.auth_service import change_password as svc_change_pw
    await svc_change_pw(current_user, req.current_password, req.new_password, db)
