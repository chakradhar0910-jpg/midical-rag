"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
from starlette.responses import Response
import time
import logging
import logging.config

from app.core.config import settings
from app.db.session import init_db
from app.api.v1.endpoints import auth, chats, documents, users, admin, ai_provider

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting MedicalRAG API...")
    await init_db()
    await seed_initial_data()
    logger.info("MedicalRAG API ready")
    yield
    logger.info("Shutting down MedicalRAG API...")


async def seed_initial_data():
    """Seed admin user and test users."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import User, UserRole, UserStatus, UserSettings
    from app.core.security import get_password_hash
    from sqlalchemy import select
    import uuid

    async with AsyncSessionLocal() as db:
        # Create admin
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                full_name="System Administrator",
                is_email_verified=True,
            )
            db.add(admin)
            await db.flush()
            admin_settings = UserSettings(user_id=admin.id)
            db.add(admin_settings)

            # Create test users
            test_users = [
                ("doctor1", "doctor1@medicalrag.com", UserRole.DOCTOR, "Dr. John Smith"),
                ("doctor2", "doctor2@medicalrag.com", UserRole.DOCTOR, "Dr. Jane Doe"),
                ("user1", "user1@medicalrag.com", UserRole.USER, "Alice Johnson"),
                ("user2", "user2@medicalrag.com", UserRole.USER, "Bob Wilson"),
                ("user3", "user3@medicalrag.com", UserRole.USER, "Carol Martinez"),
                ("user4", "user4@medicalrag.com", UserRole.USER, "David Brown"),
                ("user5", "user5@medicalrag.com", UserRole.USER, "Emma Davis"),
                ("user6", "user6@medicalrag.com", UserRole.USER, "Frank Miller"),
                ("user7", "user7@medicalrag.com", UserRole.USER, "Grace Lee"),
                ("user8", "user8@medicalrag.com", UserRole.USER, "Henry Taylor"),
            ]
            for username, email, role, full_name in test_users:
                u = User(
                    username=username,
                    email=email,
                    password_hash=get_password_hash("User@123456"),
                    role=role,
                    status=UserStatus.ACTIVE,
                    full_name=full_name,
                    is_email_verified=True,
                )
                db.add(u)
                await db.flush()
                db.add(UserSettings(user_id=u.id))

            await db.commit()
            logger.info("Seed data created: admin + 10 test users")


app = FastAPI(
    title="MedicalRAG API",
    description="Enterprise Medical RAG Chatbot Platform",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Track metrics
    if settings.PROMETHEUS_ENABLED:
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint).observe(process_time)

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(chats.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(ai_provider.router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.PROMETHEUS_ENABLED:
        return JSONResponse({"detail": "Metrics disabled"}, status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/health",
    }
