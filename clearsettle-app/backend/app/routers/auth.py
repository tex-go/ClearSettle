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

Social Auth
-----------
POST /auth/google                  → Google ID token → ClearSettle JWT
POST /auth/instagram               → Instagram OAuth code → ClearSettle JWT
GET  /auth/social                  → list linked social providers for current user
DELETE /auth/social/{provider}     → unlink a social provider
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
    SocialCompleteProfileRequest,
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
        role=req.role,
        request=request,
    )
    user_id = result["user"]["id"]
    await send_email_verification(user_id, db)
    return result


# ── Public: list roles available for self-registration ───────────────────────

@router.get("/roles")
async def get_registration_roles():
    """Public endpoint — returns roles a user can select during self-registration."""
    return {
        "roles": [
            {
                "id": "company_admin",
                "name": "Organization Owner",
                "description": "Full access to organization, users, reports, reconciliation and settings.",
                "icon": "crown",
            },
            {
                "id": "finance_manager",
                "name": "Finance Manager",
                "description": "Manage settlements, reconciliation, disputes and financial reports.",
                "icon": "account_balance",
            },
            {
                "id": "accountant",
                "name": "Accountant",
                "description": "Upload reports, view reconciliation and GST data.",
                "icon": "calculate",
            },
            {
                "id": "reconciliation_analyst",
                "name": "Reconciliation Executive",
                "description": "View and run reconciliation across all marketplaces.",
                "icon": "compare_arrows",
            },
            {
                "id": "gst_consultant",
                "name": "GST Executive",
                "description": "Access GST modules — view, file and export GST returns.",
                "icon": "receipt_long",
            },
            {
                "id": "branch_manager",
                "name": "Operations Manager",
                "description": "Manage branch operations, upload reports and resolve disputes.",
                "icon": "manage_accounts",
            },
            {
                "id": "auditor",
                "name": "Auditor",
                "description": "Read-only access across all modules including audit logs.",
                "icon": "policy",
            },
            {
                "id": "ca_admin",
                "name": "CA / Chartered Accountant",
                "description": "Access client data for review, reconciliation and GST filing.",
                "icon": "verified_user",
            },
            {
                "id": "viewer",
                "name": "Viewer",
                "description": "Read-only access to settlements and reports.",
                "icon": "visibility",
            },
        ]
    }


# ── Email availability check ─────────────────────────────────────────────────

@router.post("/check-email")
async def check_email(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Returns available:true if the email is not yet registered."""
    from app.services.auth_service import get_user_by_email
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    user = await get_user_by_email(email, db)
    return {"available": user is None}


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

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Always returns 200 — never reveals whether the email exists (anti-enumeration)."""
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


# ── Social Auth ────────────────────────────────────────────────────────────────
# All social auth endpoints follow the same response shape as /auth/login.

from pydantic import BaseModel as _BM
from typing import Optional as _Opt

class GoogleAuthRequest(_BM):
    id_token: str       # Google ID token from flutter google_sign_in

class InstagramAuthRequest(_BM):
    code:         _Opt[str] = None           # authorization code from OAuth redirect
    access_token: _Opt[str] = None           # or an existing access token
    redirect_uri: _Opt[str] = None           # must match what was used in the OAuth flow
    use_meta_graph: bool = False             # True for Facebook Login / business accounts


def _social_response(result, user) -> dict:
    """Build a login response identical in shape to /auth/login."""
    return {
        "access_token":   result.access_token,
        "token_type":     "bearer",
        "refresh_token":  result.refresh_token,
        "user": {
            "id":             str(user.id),
            "email":          user.email,
            "name":           user.name,
            "role":           user.role,
            "email_verified": user.email_verified,
        },
        "is_new_user":    result.is_new_user,
        "is_new_link":    result.is_new_link,
        "needs_email":    result.needs_email,     # True for Instagram personal accounts
        "placeholder_email": result.placeholder_email,
    }


@router.post("/google")
async def login_with_google(
    req: GoogleAuthRequest,
    db:  AsyncSession = Depends(get_db),
):
    """
    Authenticate with a Google ID token.

    Flow:
        1. Flutter google_sign_in authenticates the user
        2. Send googleSignIn.currentUser.authentication.idToken here
        3. Backend verifies the token with Google's JWKS endpoint
        4. Finds or creates a ClearSettle user
        5. Returns access_token + refresh_token (identical shape to /auth/login)

    Google Cloud Console setup:
        - Create OAuth 2.0 Client IDs for Android, iOS, and Web
        - Set GOOGLE_CLIENT_ID env var to the Web client ID (or comma-separated list)
        - The Android/iOS client IDs must be registered in the Meta app as well
    """
    from app.services.social_auth.google_auth import verify_google_token
    from app.services.social_auth.provider_service import SocialAuthService, SocialProfile
    from sqlalchemy import select
    from app.db.models.user import User

    try:
        gprofile = await verify_google_token(req.id_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Google token verification failed: {str(e)[:200]}",
        )

    profile = SocialProfile(
        provider         = "google",
        provider_user_id = gprofile.sub,
        email            = gprofile.email,
        name             = gprofile.name,
        picture          = gprofile.picture,
        email_verified   = gprofile.email_verified,
        extra            = {"locale": gprofile.locale, "hd": gprofile.hd},
    )

    svc = SocialAuthService()
    try:
        result = await svc.authenticate(profile, db)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    user = await db.get(User, result.user_id)
    return _social_response(result, user)


@router.post("/instagram")
async def login_with_instagram(
    req: InstagramAuthRequest,
    db:  AsyncSession = Depends(get_db),
):
    """
    Authenticate with Instagram OAuth.

    Flow:
        1. Flutter opens Instagram OAuth URL via flutter_web_auth_2
        2. Instagram redirects to clearsettle://oauth/instagram/callback?code=...
        3. Send the code here (code field)
        4. Backend exchanges code for token, fetches profile
        5. Returns access_token + refresh_token

    Instagram Basic Display API (personal accounts):
        - Returns id + username only (no email)
        - A placeholder email is generated: instagram_{id}@social.clearsettle.app
        - needs_email=True in the response — prompt user to enter their email

    Meta Graph API (business accounts, use_meta_graph=true):
        - Returns id + name + email (if user granted email permission)
        - needs_email=False if email was returned

    Meta App setup:
        - Create a Meta App at https://developers.facebook.com/
        - Add Instagram Basic Display product
        - Set INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, INSTAGRAM_REDIRECT_URI env vars
        - Add clearsettle://oauth/instagram/callback as a valid OAuth redirect URI
    """
    from app.services.social_auth.instagram_auth import verify_instagram_token
    from app.services.social_auth.provider_service import SocialAuthService, SocialProfile
    from app.db.models.user import User

    if not req.code and not req.access_token:
        raise HTTPException(
            status_code=400,
            detail="Either 'code' (OAuth authorization code) or 'access_token' must be provided.",
        )

    try:
        igprofile = await verify_instagram_token(
            code=req.code,
            access_token=req.access_token,
            use_meta_graph=req.use_meta_graph,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Instagram authentication failed: {str(e)[:200]}",
        )

    from datetime import datetime, timedelta
    profile = SocialProfile(
        provider         = "instagram",
        provider_user_id = igprofile.provider_id,
        email            = igprofile.email,
        name             = igprofile.name,
        picture          = igprofile.picture,
        username         = igprofile.username,
        access_token     = igprofile.access_token,
        email_verified   = igprofile.email is not None,
    )

    svc = SocialAuthService()
    try:
        result = await svc.authenticate(profile, db)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    user = await db.get(User, result.user_id)
    return _social_response(result, user)


@router.get("/social")
async def list_social_accounts(
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all linked social identity providers for the current user."""
    from app.services.social_auth.provider_service import SocialAuthService
    svc = SocialAuthService()
    providers = await svc.list_linked_providers(user.id, db)
    return {"providers": providers}


@router.post("/social/complete-profile", status_code=200)
async def social_complete_profile(
    req:  SocialCompleteProfileRequest,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Called by first-time social-login users to fill in business details.

    Social login creates a placeholder company ('{Name}'s Company') and no phone.
    This endpoint updates:
      - user.phone, user.role
      - company.name, company.state, company.city, company.gstin
    """
    from sqlalchemy import select
    from app.db.models.company import Company

    # Update user fields
    user.phone = req.phone
    user.role  = req.role

    # Update the user's primary company
    result = await db.execute(
        select(Company).where(Company.user_id == user.id).limit(1)
    )
    company = result.scalar_one_or_none()
    if company:
        company.name  = req.company_name
        company.state = req.state
        if req.city:
            company.city  = req.city
        if req.gstin:
            company.gstin = req.gstin
    else:
        company = Company(
            id=__import__("uuid").uuid4(),
            user_id=user.id,
            name=req.company_name,
            state=req.state,
            city=req.city,
            gstin=req.gstin,
        )
        db.add(company)

    await db.commit()
    return {"detail": "Profile updated successfully."}


@router.delete("/social/{provider}", status_code=200)
async def unlink_social_account(
    provider: str,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Unlink a social identity provider from the current account.

    Fails with 400 if this is the user's only authentication method
    (no password + no other social accounts).
    """
    from app.services.social_auth.provider_service import SocialAuthService
    svc = SocialAuthService()
    try:
        await svc.unlink_provider(user.id, provider, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"detail": f"{provider.title()} account unlinked successfully."}
