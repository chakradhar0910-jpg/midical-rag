"""Authentication service handling login, register, tokens, MFA."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
import logging

from app.models.models import User, Session, UserSettings, UserStatus, UserRole, Notification
from app.schemas.schemas import RegisterRequest, LoginRequest
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, decode_token, generate_secure_token,
    generate_totp_secret, verify_totp, get_totp_uri, TokenType
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _aware(dt):
    """Ensure a datetime is timezone-aware (UTC). SQLite drops tzinfo; Postgres preserves it."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> User:
        """Register a new user."""
        # Check username uniqueness
        existing = await db.execute(select(User).where(User.username == data.username.lower()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")

        # Check email uniqueness
        existing = await db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        verify_token = generate_secure_token()
        user = User(
            username=data.username.lower(),
            email=data.email.lower(),
            password_hash=get_password_hash(data.password),
            full_name=data.full_name,
            role=UserRole.USER,
            status=UserStatus.PENDING,
            email_verify_token=verify_token,
        )
        db.add(user)
        await db.flush()

        # Create default settings
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)

        # Welcome notification
        notification = Notification(
            user_id=user.id,
            title="Welcome to MedicalRAG!",
            message="Your account has been created. Please verify your email to get started.",
            type="info",
        )
        db.add(notification)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user registered: {user.email}")
        return user

    @staticmethod
    async def login(
        db: AsyncSession, data: LoginRequest, ip_address: str = "", user_agent: str = ""
    ) -> Tuple[User, str, str]:
        """Authenticate user and create session."""
        result = await db.execute(select(User).where(User.email == data.email.lower()))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check lockout
        if user.locked_until and _aware(user.locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail=f"Account locked. Try again after {user.locked_until.isoformat()}")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
                await db.commit()
                raise HTTPException(status_code=423, detail="Account locked due to too many failed attempts")
            await db.commit()
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

        if user.status == UserStatus.INACTIVE:
            raise HTTPException(status_code=403, detail="Account inactive.")

        if user.status == UserStatus.PENDING:
            raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

        # MFA verification
        if user.is_mfa_enabled:
            if not data.mfa_token:
                raise HTTPException(status_code=428, detail="MFA token required")
            if not verify_totp(user.mfa_secret, data.mfa_token):
                raise HTTPException(status_code=401, detail="Invalid MFA token")

        # Reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        # Create session
        session = Session(
            user_id=user.id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        await db.commit()
        return user, access_token, refresh_token

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token: str) -> Tuple[str, str]:
        """Refresh access token using refresh token."""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != TokenType.REFRESH:
                raise HTTPException(status_code=401, detail="Invalid token type")
            user_id = payload.get("sub")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        result = await db.execute(
            select(Session).where(Session.refresh_token == refresh_token, Session.is_active == True)
        )
        session = result.scalar_one_or_none()
        if not session or _aware(session.expires_at) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        # Rotate tokens
        new_access = create_access_token(user.id, user.role.value)
        new_refresh = create_refresh_token(user.id)

        session.refresh_token = new_refresh
        session.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return new_access, new_refresh

    @staticmethod
    async def logout(db: AsyncSession, refresh_token: str) -> None:
        """Invalidate user session."""
        result = await db.execute(select(Session).where(Session.refresh_token == refresh_token))
        session = result.scalar_one_or_none()
        if session:
            session.is_active = False
            await db.commit()

    @staticmethod
    async def setup_mfa(db: AsyncSession, user: User) -> Tuple[str, str]:
        """Setup MFA for user."""
        secret = generate_totp_secret()
        qr_uri = get_totp_uri(secret, user.email)
        user.mfa_secret = secret
        await db.commit()
        return secret, qr_uri

    @staticmethod
    async def enable_mfa(db: AsyncSession, user: User, token: str) -> None:
        """Enable MFA after verification."""
        if not user.mfa_secret:
            raise HTTPException(status_code=400, detail="MFA setup not initiated")
        if not verify_totp(user.mfa_secret, token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        user.is_mfa_enabled = True
        await db.commit()

    @staticmethod
    async def disable_mfa(db: AsyncSession, user: User, token: str) -> None:
        """Disable MFA."""
        if not user.is_mfa_enabled:
            raise HTTPException(status_code=400, detail="MFA not enabled")
        if not verify_totp(user.mfa_secret, token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        user.is_mfa_enabled = False
        user.mfa_secret = None
        await db.commit()

    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> Optional[str]:
        """Generate password reset token."""
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return None  # Don't leak user existence
        token = generate_secure_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.commit()
        return token

    @staticmethod
    async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
        """Reset password using token."""
        result = await db.execute(
            select(User).where(User.password_reset_token == token)
        )
        user = result.scalar_one_or_none()
        if not user or not user.password_reset_expires:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        if _aware(user.password_reset_expires) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token has expired")

        user.password_hash = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> None:
        """Verify email address."""
        result = await db.execute(select(User).where(User.email_verify_token == token))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        user.is_email_verified = True
        user.status = UserStatus.ACTIVE
        user.email_verify_token = None
        await db.commit()
