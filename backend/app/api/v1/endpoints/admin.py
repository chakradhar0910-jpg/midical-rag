"""Admin API endpoints for user management, analytics, and logs."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.api.v1.deps import require_admin
from app.db.session import get_db
from app.models.models import (Analytics, AuditLog, Chat, Document, Message,
                               User, UserStatus)
from app.schemas.schemas import (AdminStatsResponse, AdminUserUpdate,
                                 AnalyticsDataPoint, AnalyticsResponse,
                                 AuditLogResponse, MessageOut, UserBase,
                                 UserSummary)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get platform-wide statistics."""
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(
            select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
        )
    ).scalar() or 0
    new_users_today = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= today))
    ).scalar() or 0
    total_chats = (await db.execute(select(func.count(Chat.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    processed_docs = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "processed")
        )
    ).scalar() or 0
    ai_today = (
        await db.execute(
            select(func.count(Message.id)).where(
                Message.role == "assistant",
                Message.created_at >= today,
            )
        )
    ).scalar() or 0
    total_tokens = (
        await db.execute(select(func.coalesce(func.sum(Message.tokens_used), 0)))
    ).scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        new_users_today=new_users_today,
        total_chats=total_chats,
        total_messages=total_messages,
        total_documents=total_docs,
        processed_documents=processed_docs,
        ai_requests_today=ai_today,
        total_tokens_used=total_tokens,
    )


@router.get("/users", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users with pagination and filtering."""
    query = select(User)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.username.ilike(f"%{search}%")
        )
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    query = query.order_by(User.created_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    users = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    return {
        "users": [UserSummary.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}", response_model=UserBase)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserBase)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user role or status (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role:
        user.role = data.role
    if data.status:
        user.status = data.status
    if data.full_name:
        user.full_name = data.full_name

    log = AuditLog(
        user_id=current_user.id,
        action="user_update",
        resource_type="user",
        resource_id=user_id,
        details=data.model_dump(exclude_none=True),
    )
    db.add(log)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=MessageOut)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a user account."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log = AuditLog(
        user_id=current_user.id,
        action="user_delete",
        resource_type="user",
        resource_id=user_id,
        details={"email": user.email},
    )
    db.add(log)
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}


@router.get("/logs", response_model=dict)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get audit logs."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    logs = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    # Enrich with usernames
    log_data = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "status": log.status,
            "created_at": log.created_at.isoformat(),
        }
        if log.user_id:
            user_result = await db.execute(
                select(User.username).where(User.id == log.user_id)
            )
            username = user_result.scalar_one_or_none()
            log_dict["username"] = username
        log_data.append(log_dict)

    return {"logs": log_data, "total": total, "page": page, "page_size": page_size}


@router.get("/analytics/users", response_model=AnalyticsResponse)
async def users_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get user registration analytics."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date_trunc("day", User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= start_date)
        .group_by("date")
        .order_by("date")
    )
    rows = result.all()
    data = [AnalyticsDataPoint(date=row.date, value=float(row.count)) for row in rows]
    total = sum(d.value for d in data)

    return AnalyticsResponse(
        metric="user_registrations",
        data=data,
        total=total,
        change_percent=0.0,
    )


@router.get("/analytics/chats", response_model=AnalyticsResponse)
async def chats_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get chat activity analytics."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date_trunc("day", Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .where(Message.created_at >= start_date, Message.role == "assistant")
        .group_by("date")
        .order_by("date")
    )
    rows = result.all()
    data = [AnalyticsDataPoint(date=row.date, value=float(row.count)) for row in rows]
    total = sum(d.value for d in data)
    return AnalyticsResponse(
        metric="ai_responses", data=data, total=total, change_percent=0.0
    )


@router.get("/documents", response_model=dict)
async def list_all_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all documents (admin view)."""
    query = select(Document).order_by(Document.created_at.desc())
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    docs = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {
        "documents": list(docs),
        "total": total,
        "page": page,
        "page_size": page_size,
    }
