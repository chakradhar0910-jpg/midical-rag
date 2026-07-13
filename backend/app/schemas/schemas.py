"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


# ─── Base ────────────────────────────────────────────────────────────────────

class BaseResponse(BaseModel):
    class Config:
        from_attributes = True


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username must be 3-50 chars, alphanumeric and underscore only")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str


class MFAVerifyRequest(BaseModel):
    token: str


# ─── User ────────────────────────────────────────────────────────────────────

class UserBase(BaseResponse):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    phone: Optional[str]
    role: str
    status: str
    is_email_verified: bool
    is_mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime


class UserSummary(BaseResponse):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    created_at: datetime


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    full_name: Optional[str] = None


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class ChatResponse(BaseResponse):
    id: str
    user_id: str
    title: str
    is_pinned: bool
    is_archived: bool
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ChatListResponse(BaseModel):
    chats: List[ChatResponse]
    total: int
    page: int
    page_size: int


class MessageCreate(BaseModel):
    content: str


class SourceDocument(BaseModel):
    document_id: str
    title: str
    content: str
    score: float
    page: Optional[int] = None


class MessageResponse(BaseResponse):
    id: str
    chat_id: str
    role: str
    content: str
    sources: Optional[List[SourceDocument]]
    confidence_score: Optional[float]
    tokens_used: Optional[int]
    reaction: Optional[str]
    is_flagged: bool
    processing_time_ms: Optional[int]
    model_used: Optional[str]
    created_at: datetime


class ChatWithMessages(ChatResponse):
    messages: List[MessageResponse]


class MessageReactionRequest(BaseModel):
    reaction: str


# ─── Document ────────────────────────────────────────────────────────────────

class DocumentResponse(BaseResponse):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    file_name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    source_type: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    is_public: bool
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ─── Settings ────────────────────────────────────────────────────────────────

class SettingsResponse(BaseResponse):
    theme: str
    language: str
    notifications_enabled: bool
    email_notifications: bool
    chat_history_enabled: bool
    default_model: str
    max_tokens: int
    temperature: float


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    chat_history_enabled: Optional[bool] = None
    default_model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


# ─── Admin ────────────────────────────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    new_users_today: int
    total_chats: int
    total_messages: int
    total_documents: int
    processed_documents: int
    ai_requests_today: int
    total_tokens_used: int


class AuditLogResponse(BaseResponse):
    id: str
    user_id: Optional[str]
    username: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime


class AnalyticsDataPoint(BaseModel):
    date: datetime
    value: float
    label: Optional[str] = None


class AnalyticsResponse(BaseModel):
    metric: str
    data: List[AnalyticsDataPoint]
    total: float
    change_percent: float


# ─── API Keys ────────────────────────────────────────────────────────────────

class APIKeyCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseResponse):
    id: str
    name: str
    key_prefix: str
    permissions: Optional[List[str]]
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyCreatedResponse(APIKeyResponse):
    api_key: str  # Full key shown only on creation


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationResponse(BaseResponse):
    id: str
    title: str
    message: str
    type: str
    is_read: bool
    action_url: Optional[str]
    created_at: datetime


# ─── Generic ─────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    message: str


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    search: Optional[str] = None


# ─── AI Provider ──────────────────────────────────────────────────────────────

class AIProviderHealth(BaseModel):
    ollama_running:     bool
    available_models:   List[str]
    gemini_available:   bool
    default_provider:   str


class AIProviderInfo(BaseModel):
    provider_used:  str
    provider_tag:   str
    model_used:     str
