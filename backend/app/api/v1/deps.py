"""FastAPI dependency injection utilities."""

import logging
from typing import Optional

from app.core.security import RolePermissions, decode_token
from app.db.session import get_db
from app.models.models import User, UserRole, UserStatus
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active."""
    if current_user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Account suspended")
    if current_user.status == UserStatus.INACTIVE:
        raise HTTPException(status_code=403, detail="Account inactive")
    return current_user


def require_role(*roles: str):
    """Role-based access control decorator factory."""

    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker


def require_permission(permission: str):
    """Permission-based access control decorator factory."""

    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not RolePermissions.has_permission(current_user.role.value, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return current_user

    return permission_checker


require_admin = require_role("admin")
require_doctor_or_admin = require_role("admin", "doctor")
