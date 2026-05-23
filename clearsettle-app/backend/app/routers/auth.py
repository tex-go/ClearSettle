"""
Auth router.

Endpoints
---------
POST /auth/login                   → issue access + refresh tokens
POST /auth/register                → create user + company, issue tokens
POST /auth/refresh                 → rotate refresh token, issue new pair
POST /auth/logout                  → revoke refresh token
GET  /auth/me                      → current user profile
PUT  /auth/me                      → update display name
POST /auth/change-password         → change password + revoke all refresh tokens
POST /auth/forgot-password         → send password reset email
POST /auth/reset-password          → redeem reset token, set new password
POST /auth/send-verification       → resend email verification link
POST /auth/verify-email            → verify email address via token
POST /auth/invite                  → invite a team member (admin only)
POST /auth/accept-invite           → accept invitation, create / link account
GET  /auth/permissions             → list permission strings for current role
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rate_limiter import login_rate_limiter
from app.schemas.auth import (
    AccessTokenResponse,
    AcceptInviteRequest,
    ForgotPasswordRequest,
    InviteRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import ChangePasswordRequest, UpdateProfileRequest, UserProfile

router = APIRouter()


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    key = req.email.lower()
    login_rate_limiter.check(key)
    try:
        from app.services.auth_service import login as svc_login
        result = await svc_login(req.email, req.password, db, request=request)
        login_rate_limiter.reset(key)
        return result
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            login_rate_limiter.record_failure(key)
        raise


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import register as svc_register, send_email_verification
    result = await svc_register(
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
    # Fire-and-forget email verification (errors are swallowed inside the service)
    user_id = result["user"]["id"]
    await send_email_verification(user_id, db)
    return result


# ── Refresh token ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import refresh_tokens
    return await refresh_tokens(req.refresh_token, db)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: LogoutRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import logout as svc_logout
    await svc_logout(req.refresh_token, db)


# ── Current user ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def me(current_user=Depends(get_current_user)):
    from app.core.rbac import ROLE_PERMISSIONS, get_user_role
    role = get_user_role(current_user)
    permissions = sorted(ROLE_PERMISSIONS.get(role, set()))
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
    from app.core.rbac import ROLE_PERMISSIONS, get_user_role
    role = get_user_role(current_user)
    return {"role": role, "permissions": sorted(ROLE_PERMISSIONS.get(role, set()))}


# ── Update profile ────────────────────────────────────────────────────────────

@router.put("/me")
async def update_profile(
    req: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.name is not None:
        current_user.name = req.name
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
    from app.services.auth_service import change_password as svc_change_pw
    await svc_change_pw(current_user, req.current_password, req.new_password, db)


# ── Forgot password ───────────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Always returns 202 — never reveals whether the email exists."""
    from app.services.auth_service import forgot_password as svc_forgot
    await svc_forgot(req.email, db)
    return {"detail": "If that email is registered, a reset link has been sent."}


# ── Reset password ────────────────────────────────────────────────────────────

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import reset_password as svc_reset
    await svc_reset(req.token, req.new_password, db)


# ── Email verification ────────────────────────────────────────────────────────

@router.post("/send-verification", status_code=status.HTTP_202_ACCEPTED)
async def send_verification(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth_service import send_email_verification
    await send_email_verification(current_user.id, db)
    return {"detail": "Verification email sent."}


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import verify_email as svc_verify
    await svc_verify(req.token, db)


# ── Team invitations ──────────────────────────────────────────────────────────

@router.post("/invite", status_code=status.HTTP_202_ACCEPTED)
async def invite_member(
    req: InviteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.rbac import get_user_role
    role = get_user_role(current_user)
    if role not in ("admin", "super_admin", "org_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins can invite team members")

    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No company associated with your account")

    from app.services.auth_service import invite_member as svc_invite
    await svc_invite(current_user, req.email, req.role, company.id, db)
    return {"detail": "Invitation sent."}


@router.post("/accept-invite", status_code=status.HTTP_201_CREATED)
async def accept_invite(req: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    from app.services.auth_service import accept_invitation
    return await accept_invitation(req.token, req.password, req.name, db)
