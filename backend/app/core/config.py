"""Application configuration settings."""

import secrets
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MedicalRAG"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://medrag:medrag_pass@postgres:5432/medicalrag"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "medical_documents"

    # ── AI Provider Routing ───────────────────────────────────────────────────
    # Default provider: "ollama" | "gemini" | "auto"
    DEFAULT_AI_PROVIDER: str = "auto"

    # Embedding Provider: "openai" | "gemini" | "ollama"
    EMBEDDING_PROVIDER: str = "openai"

    # OpenAI (used for embeddings only — not for chat generation)
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Gemini (cloud LLM)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0

    # Ollama (local LLM)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_DEFAULT_MODEL: str = ""  # empty = auto-discover
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@medicalrag.com"

    # Admin
    ADMIN_EMAIL: str = "admin@medicalrag.com"
    ADMIN_PASSWORD: str = "Admin@123456"
    ADMIN_USERNAME: str = "admin"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,csv,md"

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip() for e in self.ALLOWED_EXTENSIONS.split(",")]

    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
