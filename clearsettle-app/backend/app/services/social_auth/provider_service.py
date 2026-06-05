"""
SocialAuthService — provider-agnostic account linking logic.

This service handles the "find or create" logic that is identical for all
identity providers (Google, Instagram, Microsoft, Apple, etc.).

Flow for every provider:
  1. Validate token with IdP  → SocialProfile
  2. Look up social_accounts by (provider, provider_user_id)  → existing row?
     YES: update token, update last_used_at → load User → return JWT
     NO:  check if email already in users table → existing user?
       YES: link social account to existing user (email-based account linking)
       NO:  create new User + Company + link social account
  3. Issue JWT + refresh token → return to caller

Security rules:
  - If provider_email differs from the users.email that was found, still link —
    the user may have changed their email on either side.
  - Never update users.email from the provider email silently — that would allow
    account takeover via Google-side email change.
  - Tokens are always Fernet-encrypted before storage.
  - Never log any token value.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt, decrypt
from app.core.security import create_access_token, create_refresh_token
from app.db.models.refresh_token import RefreshToken
from app.db.models.social_account import SocialAccount
from app.db.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class SocialProfile:
    """Normalised identity data returned by any IdP validator."""
    provider: str           # google | instagram | microsoft | apple | linkedin
    provider_user_id: str   # stable IdP user ID
    email: Optional[str]    # real email or None (Instagram personal accounts)
    name: Optional[str]
    picture: Optional[str]
    username: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token_value: Optional[str] = None
    token_expiry: Optional[datetime] = None
    token_scope: Optional[str] = None
    email_verified: bool = True
    extra: dict = field(default_factory=dict)


@dataclass
class SocialAuthResult:
    user_id: UUID
    access_token: str
    refresh_token: str
    is_new_user: bool
    is_new_link: bool           # social account was newly linked to an existing user
    needs_email: bool = False   # True when no email from IdP (Instagram personal accounts)
    placeholder_email: str = ""


class SocialAuthService:
    """Provider-agnostic social authentication service."""

    async def authenticate(
        self,
        profile: SocialProfile,
        db: AsyncSession,
    ) -> SocialAuthResult:
        """
        Find or create a user for a social profile, then issue JWT + refresh token.

        Steps:
          1. Look up (provider, provider_user_id) in social_accounts
          2. If not found: look up users by email (account linking)
          3. If not found by email: create new user
          4. Upsert social_account row with latest token
          5. Issue JWT + refresh token
        """
        # ── Step 1: Lookup by IdP stable ID ──────────────────────────────────
        social_row = (
            await db.execute(
                select(SocialAccount).where(
                    SocialAccount.provider == profile.provider,
                    SocialAccount.provider_user_id == profile.provider_user_id,
                )
            )
        ).scalar_one_or_none()

        is_new_user = False
        is_new_link = False

        if social_row:
            # Existing social account → load user
            user = await db.get(User, social_row.user_id)
            if not user or not user.is_active:
                raise PermissionError("Account is inactive.")
            logger.info(
                "Social login: existing account",
                extra={
                    "provider":   profile.provider,
                    "user_id":    str(user.id),
                    "is_new":     False,
                },
            )
        else:
            # ── Step 2: Lookup by email ───────────────────────────────────────
            user = None
            effective_email = self._effective_email(profile)

            if effective_email and not effective_email.endswith("@social.clearsettle.app"):
                user = (
                    await db.execute(
                        select(User).where(
                            User.email == effective_email,
                            User.deleted_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()

            if user:
                # Link social account to existing user (email match)
                is_new_link = True
                logger.info(
                    "Social login: linking to existing email-based account",
                    extra={
                        "provider": profile.provider,
                        "user_id":  str(user.id),
                        "email":    effective_email,
                    },
                )
            else:
                # ── Step 3: Create new user ───────────────────────────────────
                user = await self._create_user(profile, effective_email, db)
                is_new_user = True
                logger.info(
                    "Social login: new user created",
                    extra={
                        "provider": profile.provider,
                        "user_id":  str(user.id),
                        "email":    effective_email,
                    },
                )

            # ── Step 4: Create social_account row ─────────────────────────────
            social_row = SocialAccount(
                id=uuid.uuid4(),
                user_id=user.id,
                provider=profile.provider,
                provider_user_id=profile.provider_user_id,
                provider_email=profile.email,
                provider_name=profile.name,
                profile_picture_url=profile.picture,
                provider_username=profile.username,
                is_primary=is_new_user,   # first-ever social login is the primary
            )
            db.add(social_row)

        # ── Update social_account token fields ────────────────────────────────
        social_row.last_used_at = datetime.utcnow()
        social_row.provider_name = profile.name or social_row.provider_name
        social_row.profile_picture_url = profile.picture or social_row.profile_picture_url

        if profile.access_token:
            social_row.access_token_enc = encrypt(profile.access_token)
        if profile.refresh_token_value:
            social_row.refresh_token_enc = encrypt(profile.refresh_token_value)
        if profile.token_expiry:
            social_row.token_expiry = profile.token_expiry
        if profile.token_scope:
            social_row.token_scope = profile.token_scope

        # ── Step 5: Issue ClearSettle JWT + refresh token ─────────────────────
        access_jwt = create_access_token({"sub": str(user.id), "email": user.email})
        raw_refresh, hashed_refresh = create_refresh_token()

        db.add(RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hashed_refresh,
            expires_at=datetime.utcnow() + timedelta(days=7),
        ))

        await db.commit()

        needs_email = profile.email is None
        placeholder = self._effective_email(profile) if needs_email else ""

        return SocialAuthResult(
            user_id       = user.id,
            access_token  = access_jwt,
            refresh_token = raw_refresh,
            is_new_user   = is_new_user,
            is_new_link   = is_new_link,
            needs_email   = needs_email,
            placeholder_email = placeholder,
        )

    async def unlink_provider(
        self,
        user_id: UUID,
        provider: str,
        db: AsyncSession,
    ) -> None:
        """
        Remove a social account link.

        Raises ValueError if this is the user's only login method
        (no password + no other social accounts).
        """
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found.")

        # Count remaining auth methods after removing this one
        other_socials = (
            await db.execute(
                select(SocialAccount).where(
                    SocialAccount.user_id == user_id,
                    SocialAccount.provider != provider,
                )
            )
        ).scalars().all()

        has_password = bool(user.hashed_password)
        if not has_password and not other_socials:
            raise ValueError(
                "Cannot unlink — this is your only login method. "
                "Set a password first."
            )

        # Delete the social account row
        social_row = (
            await db.execute(
                select(SocialAccount).where(
                    SocialAccount.user_id == user_id,
                    SocialAccount.provider == provider,
                )
            )
        ).scalar_one_or_none()

        if social_row:
            await db.delete(social_row)
            await db.commit()
            logger.info(
                "Social account unlinked",
                extra={"user_id": str(user_id), "provider": provider},
            )

    async def list_linked_providers(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Return all linked social accounts for a user (without tokens)."""
        rows = (
            await db.execute(
                select(SocialAccount).where(SocialAccount.user_id == user_id)
            )
        ).scalars().all()

        return [
            {
                "provider":          r.provider,
                "provider_email":    r.provider_email,
                "provider_name":     r.provider_name,
                "profile_picture_url": r.profile_picture_url,
                "provider_username": r.provider_username,
                "is_primary":        r.is_primary,
                "linked_at":         r.created_at.isoformat(),
                "last_used_at":      r.last_used_at.isoformat() if r.last_used_at else None,
            }
            for r in rows
        ]

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _effective_email(profile: SocialProfile) -> str:
        """
        Return the email to use for account matching / user creation.
        If the IdP provides no email (Instagram personal accounts),
        generate a deterministic placeholder that the user can update later.
        """
        if profile.email:
            return profile.email.lower().strip()
        # Placeholder — provider-specific, deterministic, not a real inbox
        return f"{profile.provider}_{profile.provider_user_id}@social.clearsettle.app"

    @staticmethod
    async def _create_user(
        profile: SocialProfile,
        email: str,
        db: AsyncSession,
    ) -> User:
        """Create a new User row for a social-only account."""
        from app.db.models.company import Company

        display_name = (
            profile.name
            or profile.username
            or email.split("@")[0].replace("_", " ").title()
        )

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=None,      # no password for social-only accounts
            name=display_name,
            role="admin",
            is_active=True,
            email_verified=profile.email_verified,
        )
        db.add(user)
        await db.flush()   # get user.id before creating company

        # Create a default company (matches existing email/password flow)
        company = Company(
            id=uuid.uuid4(),
            user_id=user.id,
            name=f"{display_name}'s Company",
        )
        db.add(company)
        # don't commit here — caller handles transaction

        return user
