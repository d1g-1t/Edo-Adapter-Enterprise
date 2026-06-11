from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.base import Base
from src.infrastructure.database.models import ApiUserModel, TenantModel

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> TenantModel:
    t = TenantModel(id=uuid.uuid4(), name="Test Tenant", slug="test-tenant", is_active=True)
    db_session.add(t)
    await db_session.commit()
    return t


@pytest_asyncio.fixture
async def api_user(db_session: AsyncSession, tenant: TenantModel) -> ApiUserModel:
    u = ApiUserModel(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="test@example.com",
        hashed_password=_pwd_ctx.hash("password123"),
        role="admin",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    return u


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, api_user: ApiUserModel) -> AsyncGenerator[AsyncClient, None]:
    from src.main import create_app
    from src.presentation.deps import get_db

    app = create_app()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def access_token(api_user: ApiUserModel, tenant: TenantModel) -> str:
    from src.core.security import create_access_token
    return create_access_token(
        str(api_user.id),
        extra={"tenant_id": str(tenant.id), "role": "admin"},
    )


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
