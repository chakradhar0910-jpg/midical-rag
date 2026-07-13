"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    PasswordResetRequest, PasswordResetConfirm, VerifyEmailRequest,
    MFASetupResponse, MFAVerifyRequest, MessageOut, ChangePasswordRequest
)
from app.services.auth.auth_service import AuthService
from app.services.email_service import EmailService
from app.api.v1.deps import get_current_user, get_current_active_user
from app.models.models import User, AuditLog, AuditAction
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_info(request: Request):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    ua = request.headers.get("User-Agent", "")
    return ip, ua


@router.post("/register", response_model=MessageOut, status_code=201)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    user = await AuthService.register(db, data)
    ip, ua = get_client_info(request)
    log = AuditLog(
        user_id=user.id,
        action=AuditAction.REGISTER,
        ip_address=ip,
        user_agent=ua,
        details={"email": user.email},
    )
    db.add(log)
    await db.commit()
    
    # Send verification email in background
    if user.email_verify_token:
        background_tasks.add_task(EmailService.send_verification_email, user.email, user.email_verify_token)
        
    return {"message": "Registration successful. Please check your email to verify your account."}


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens."""
    ip, ua = get_client_info(request)
    user, access_token, refresh_token = await AuthService.login(db, data, ip, ua)

    log = AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        ip_address=ip,
        user_agent=ua,
        details={"email": user.email},
    )
    db.add(log)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    access_token, new_refresh = await AuthService.refresh_token(db, data.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageOut)
async def logout(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Logout and invalidate session."""
    await AuthService.logout(db, data.refresh_token)
    ip, ua = get_client_info(request)
    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/verify-email", response_model=MessageOut)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email address with token."""
    await AuthService.verify_email(db, data.token)
    return {"message": "Email verified successfully. You can now login."}


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email."""
    token = await AuthService.request_password_reset(db, data.email)
    if token:
        background_tasks.add_task(EmailService.send_password_reset_email, data.email, token)
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token."""
    await AuthService.reset_password(db, data.token, data.password)
    return {"message": "Password reset successfully. Please login with your new password."}


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Setup multi-factor authentication."""
    secret, qr_uri = await AuthService.setup_mfa(db, current_user)
    return MFASetupResponse(secret=secret, qr_uri=qr_uri)


@router.post("/mfa/enable", response_model=MessageOut)
async def enable_mfa(
    data: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Enable MFA after verifying token."""
    await AuthService.enable_mfa(db, current_user, data.token)
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable", response_model=MessageOut)
async def disable_mfa(
    data: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Disable MFA."""
    await AuthService.disable_mfa(db, current_user, data.token)
    return {"message": "MFA disabled successfully"}


@router.post("/change-password", response_model=MessageOut)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Change user password."""
    from app.core.security import verify_password, get_password_hash
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(data.new_password)
    ip, ua = get_client_info(request)
    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.PASSWORD_CHANGE,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    await db.commit()
    return {"message": "Password changed successfully"}
