"""Unit tests for authentication service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.security import (RolePermissions, create_access_token,
                               create_refresh_token, decode_token,
                               generate_secure_token, generate_totp_secret,
                               get_password_hash, verify_password, verify_totp)


class TestPasswordHashing:
    def test_hash_password_creates_valid_hash(self):
        pwd = "TestPassword@123"
        hashed = get_password_hash(pwd)
        assert hashed != pwd
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        pwd = "TestPassword@123"
        hashed = get_password_hash(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("TestPassword@123")
        assert verify_password("WrongPassword@123", hashed) is False

    def test_different_hashes_for_same_password(self):
        pwd = "TestPassword@123"
        hash1 = get_password_hash(pwd)
        hash2 = get_password_hash(pwd)
        assert hash1 != hash2  # bcrypt uses random salt


class TestJWTTokens:
    def test_create_access_token(self):
        token = create_access_token("user-123", "user")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        token = create_access_token("user-123", "user")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert payload["role"] == "user"

    def test_create_refresh_token(self):
        token = create_refresh_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_token_has_expiry(self):
        token = create_access_token("user-123", "admin")
        payload = decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()

    def test_token_has_unique_jti(self):
        token1 = create_access_token("user-123", "user")
        token2 = create_access_token("user-123", "user")
        p1 = decode_token(token1)
        p2 = decode_token(token2)
        assert p1["jti"] != p2["jti"]

    def test_invalid_token_raises_exception(self):
        from jose import JWTError

        with pytest.raises(Exception):
            decode_token("invalid.token.here")

    def test_expired_token_raises_exception(self):
        from app.core.config import settings
        from jose import jwt

        payload = {
            "sub": "user-123",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(Exception):
            decode_token(token)


class TestMFA:
    def test_generate_totp_secret(self):
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32

    def test_verify_valid_totp(self):
        import pyotp

        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        assert verify_totp(secret, current_token) is True

    def test_verify_invalid_totp(self):
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False

    def test_generate_secure_token(self):
        token = generate_secure_token()
        assert isinstance(token, str)
        assert len(token) >= 32
        token2 = generate_secure_token()
        assert token != token2  # Unique tokens


class TestRBACPermissions:
    def test_admin_has_all_permissions(self):
        admin_perms = RolePermissions.get_permissions("admin")
        assert "users:read" in admin_perms
        assert "users:write" in admin_perms
        assert "users:delete" in admin_perms
        assert "logs:read" in admin_perms
        assert "analytics:read" in admin_perms

    def test_user_has_limited_permissions(self):
        user_perms = RolePermissions.get_permissions("user")
        assert "chats:read" in user_perms
        assert "chats:write" in user_perms
        assert "users:delete" not in user_perms
        assert "logs:read" not in user_perms

    def test_viewer_has_readonly_permissions(self):
        viewer_perms = RolePermissions.get_permissions("viewer")
        assert "chats:read" in viewer_perms
        assert "chats:write" not in viewer_perms

    def test_has_permission_returns_true(self):
        assert RolePermissions.has_permission("admin", "users:delete") is True

    def test_has_permission_returns_false(self):
        assert RolePermissions.has_permission("user", "users:delete") is False

    def test_unknown_role_returns_empty(self):
        assert RolePermissions.get_permissions("unknown_role") == []
        assert RolePermissions.has_permission("unknown_role", "users:read") is False


class TestPasswordValidation:
    """Test password strength requirements."""

    def test_valid_strong_password(self):
        from app.schemas.schemas import RegisterRequest

        data = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="StrongPass@123",
        )
        assert data.password == "StrongPass@123"

    def test_weak_password_no_uppercase(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.schemas import RegisterRequest

            RegisterRequest(username="u", email="e@e.com", password="weakpass@123")

    def test_weak_password_too_short(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.schemas import RegisterRequest

            RegisterRequest(username="u", email="e@e.com", password="Sh@1")

    def test_invalid_username_special_chars(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.schemas import RegisterRequest

            RegisterRequest(
                username="user name!", email="e@e.com", password="Valid@Pass1"
            )
