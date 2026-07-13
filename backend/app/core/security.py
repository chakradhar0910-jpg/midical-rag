"""Security utilities for JWT, password hashing, and RBAC."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import pyotp
from app.core.config import settings
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS
)


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFY = "verify"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_token(
    subject: Union[str, Any],
    token_type: str = TokenType.ACCESS,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None,
) -> str:
    """Create a JWT token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    elif token_type == TokenType.ACCESS:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    elif token_type == TokenType.REFRESH:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    elif token_type in (TokenType.RESET, TokenType.VERIFY):
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": token_type,
        "jti": secrets.token_urlsafe(16),
    }

    if extra_data:
        to_encode.update(extra_data)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: Union[str, Any], role: str = "user") -> str:
    """Create an access token."""
    return create_token(subject, TokenType.ACCESS, extra_data={"role": role})


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create a refresh token."""
    return create_token(subject, TokenType.REFRESH)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        raise


def generate_totp_secret() -> str:
    """Generate a TOTP secret for MFA."""
    return pyotp.random_base32()


def verify_totp(secret: str, token: str) -> bool:
    """Verify a TOTP token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def get_totp_uri(secret: str, email: str) -> str:
    """Get TOTP URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


class RolePermissions:
    """RBAC permission definitions."""

    PERMISSIONS = {
        "admin": [
            "users:read",
            "users:write",
            "users:delete",
            "documents:read",
            "documents:write",
            "documents:delete",
            "chats:read",
            "chats:write",
            "chats:delete",
            "analytics:read",
            "logs:read",
            "settings:read",
            "settings:write",
            "api_keys:read",
            "api_keys:write",
        ],
        "doctor": [
            "documents:read",
            "documents:write",
            "chats:read",
            "chats:write",
            "analytics:read",
        ],
        "user": [
            "documents:read",
            "chats:read",
            "chats:write",
        ],
        "viewer": [
            "documents:read",
            "chats:read",
        ],
    }

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """Check if a role has a specific permission."""
        return permission in cls.PERMISSIONS.get(role, [])

    @classmethod
    def get_permissions(cls, role: str) -> list:
        """Get all permissions for a role."""
        return cls.PERMISSIONS.get(role, [])
