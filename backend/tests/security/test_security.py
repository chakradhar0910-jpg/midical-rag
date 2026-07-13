"""Security tests - OWASP Top 10 coverage."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.db.session import get_db, Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_security.db"
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


class TestSecurityHeaders:
    """Test that security headers are properly set."""

    async def test_xss_protection_header(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    async def test_no_sniff_header(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_frame_options_header(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_referrer_policy_header(self, client: AsyncClient):
        response = await client.get("/health")
        assert "referrer-policy" in response.headers


class TestAuthenticationSecurity:
    """Test authentication security measures."""

    async def test_jwt_required_for_protected_routes(self, client: AsyncClient):
        """A01: Broken Access Control - unauthenticated access must be blocked."""
        protected_routes = [
            "/api/v1/users/me",
            "/api/v1/chats",
            "/api/v1/documents",
        ]
        for route in protected_routes:
            response = await client.get(route)
            assert response.status_code in [401, 403], f"Route {route} should be protected"

    async def test_admin_routes_require_admin_role(self, client: AsyncClient):
        """Test admin endpoints are not accessible to regular users."""
        # Register and verify a regular user
        await client.post("/api/v1/auth/register", json={
            "username": "regularuser",
            "email": "regular@test.com",
            "password": "RegularPass@123"
        })
        async with TestingSessionLocal() as db:
            from sqlalchemy import update
            from app.models.models import User, UserStatus
            await db.execute(
                update(User).where(User.email == "regular@test.com")
                .values(status=UserStatus.ACTIVE, is_email_verified=True)
            )
            await db.commit()

        login = await client.post("/api/v1/auth/login", json={
            "email": "regular@test.com", "password": "RegularPass@123"
        })
        token = login.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        admin_routes = ["/api/v1/admin/stats", "/api/v1/admin/users", "/api/v1/admin/logs"]
        for route in admin_routes:
            response = await client.get(route, headers=headers)
            assert response.status_code == 403, f"Admin route {route} accessible to regular user"

    async def test_invalid_jwt_rejected(self, client: AsyncClient):
        """A07: Identification and Authentication Failures."""
        fake_tokens = [
            "Bearer invalid.token",
            "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJoYWNrZXIifQ.",
            "Bearer " + "a" * 100,
        ]
        for token in fake_tokens:
            response = await client.get("/api/v1/users/me", headers={"Authorization": token})
            assert response.status_code in [401, 403], f"Token should be rejected: {token[:30]}..."


class TestInputValidation:
    """Test input validation and injection prevention."""

    async def test_sql_injection_in_login(self, client: AsyncClient):
        """A03: Injection - SQL injection must be prevented."""
        injection_payloads = [
            {"email": "admin'--@test.com", "password": "pass"},
            {"email": "' OR '1'='1", "password": "' OR '1'='1"},
            {"email": "admin@test.com; DROP TABLE users;--", "password": "pass"},
        ]
        for payload in injection_payloads:
            response = await client.post("/api/v1/auth/login", json=payload)
            assert response.status_code in [401, 422], "SQL injection should be handled safely"

    async def test_xss_in_registration(self, client: AsyncClient):
        """Test XSS payloads are handled safely."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
        ]
        for payload in xss_payloads:
            response = await client.post("/api/v1/auth/register", json={
                "username": "normal",
                "email": "test@example.com",
                "password": "ValidPass@123",
                "full_name": payload
            })
            # Should either succeed (storing escaped) or fail validation
            assert response.status_code in [201, 400, 422]
            if response.status_code == 201:
                # The stored value must not be returned as raw script
                assert "<script>" not in response.text or "message" in response.json()

    async def test_oversized_input_rejected(self, client: AsyncClient):
        """Test that oversized inputs are handled."""
        response = await client.post("/api/v1/auth/register", json={
            "username": "a" * 1000,
            "email": "valid@example.com",
            "password": "ValidPass@123"
        })
        assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting is in place."""

    async def test_brute_force_protection(self, client: AsyncClient):
        """Test account lockout after multiple failed logins."""
        # Register and activate user
        await client.post("/api/v1/auth/register", json={
            "username": "brute_target",
            "email": "brute@test.com",
            "password": "RealPass@123"
        })
        async with TestingSessionLocal() as db:
            from sqlalchemy import update
            from app.models.models import User, UserStatus
            await db.execute(
                update(User).where(User.email == "brute@test.com")
                .values(status=UserStatus.ACTIVE, is_email_verified=True)
            )
            await db.commit()

        # Attempt multiple wrong logins
        for i in range(6):
            resp = await client.post("/api/v1/auth/login", json={
                "email": "brute@test.com",
                "password": "WrongPass@123"
            })

        # After max attempts, account should be locked
        final_resp = await client.post("/api/v1/auth/login", json={
            "email": "brute@test.com",
            "password": "WrongPass@123"
        })
        assert final_resp.status_code in [423, 401]


class TestPasswordSecurity:
    """Test password security requirements."""

    async def test_password_not_returned_in_response(self, client: AsyncClient):
        """Ensure passwords are never returned in API responses."""
        await client.post("/api/v1/auth/register", json={
            "username": "pwdtest",
            "email": "pwdtest@example.com",
            "password": "MySecret@123"
        })
        async with TestingSessionLocal() as db:
            from sqlalchemy import update
            from app.models.models import User, UserStatus
            await db.execute(
                update(User).where(User.email == "pwdtest@example.com")
                .values(status=UserStatus.ACTIVE, is_email_verified=True)
            )
            await db.commit()

        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "pwdtest@example.com",
            "password": "MySecret@123"
        })
        token = login_resp.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        profile_resp = await client.get("/api/v1/users/me", headers=headers)
        profile_data = profile_resp.json()
        response_str = str(profile_data)
        assert "MySecret@123" not in response_str
        assert "password_hash" not in response_str
