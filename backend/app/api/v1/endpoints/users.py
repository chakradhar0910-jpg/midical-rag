"""User profile and settings API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import User, UserSettings, Notification, AuditLog, AuditAction
from app.schemas.schemas import (
    UserBase, UserUpdateRequest, SettingsResponse, SettingsUpdate, MessageOut,
    NotificationResponse
)
from app.api.v1.deps import get_current_active_user
from typing import List

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserBase)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserBase)
async def update_profile(
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update user profile."""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.PROFILE_UPDATE,
        details=data.model_dump(exclude_none=True),
    )
    db.add(log)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/settings", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get user settings."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


@router.put("/me/settings", response_model=SettingsResponse)
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update user settings."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.add(s)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(s, field, value)

    log = AuditLog(user_id=current_user.id, action=AuditAction.SETTINGS_UPDATE)
    db.add(log)
    await db.commit()
    await db.refresh(s)
    return s


@router.get("/me/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get user notifications."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/me/notifications/{notification_id}/read", response_model=MessageOut)
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()
    return {"message": "Notification marked as read"}


@router.post("/me/notifications/read-all", response_model=MessageOut)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all notifications as read."""
    from sqlalchemy import update
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}
