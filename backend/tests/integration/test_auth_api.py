"""Integration tests for authentication API endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.db.session import get_db, Base
from app.core.config import settings

# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass@123",
        "full_name": "Test User"
    })
    return {"username": "testuser", "email": "test@example.com", "password": "TestPass@123"}


@pytest_asyncio.fixture
async def verified_user(client: AsyncClient, registered_user):
    """Create a verified active user directly in DB."""
    async with TestingSessionLocal() as db:
        from sqlalchemy import select, update
        from app.models.models import User, UserStatus
        await db.execute(
            update(User).where(User.email == registered_user["email"])
            .values(status=UserStatus.ACTIVE, is_email_verified=True)
        )
        await db.commit()
    return registered_user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, verified_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": verified_user["password"]
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRegisterEndpoint:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass@123",
            "full_name": "New User"
        })
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "Registration successful" in data["message"]

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user):
        response = await client.post("/api/v1/auth/register", json={
            "username": "anotheruser",
            "email": registered_user["email"],
            "password": "AnotherPass@123"
        })
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_duplicate_username(self, client: AsyncClient, registered_user):
        response = await client.post("/api/v1/auth/register", json={
            "username": registered_user["username"],
            "email": "another@example.com",
            "password": "AnotherPass@123"
        })
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "username": "validuser",
            "email": "not-an-email",
            "password": "ValidPass@123"
        })
        assert response.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": "weak"
        })
        assert response.status_code == 422


class TestLoginEndpoint:
    async def test_login_success(self, client: AsyncClient, verified_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": verified_user["email"],
            "password": verified_user["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, verified_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": verified_user["email"],
            "password": "WrongPass@123"
        })
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "SomePass@123"
        })
        assert response.status_code == 401

    async def test_login_unverified_user(self, client: AsyncClient, registered_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        assert response.status_code in [401, 403]


class TestProtectedEndpoints:
    async def test_get_profile_with_valid_token(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data

    async def test_get_profile_without_token(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 403

    async def test_get_profile_invalid_token(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid.token"})
        assert response.status_code == 401 or response.status_code == 403


class TestHealthCheck:
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestRefreshToken:
    async def test_refresh_token_success(self, client: AsyncClient, verified_user):
        login_response = await client.post("/api/v1/auth/login", json={
            "email": verified_user["email"],
            "password": verified_user["password"]
        })
        refresh_token = login_response.json()["refresh_token"]

        refresh_response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.refresh.token"
        })
        assert response.status_code == 401
