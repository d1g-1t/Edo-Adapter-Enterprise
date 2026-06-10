from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.logging import configure_logging
from src.infrastructure.database.models import ApiUserModel, TenantModel
from src.infrastructure.database.session import engine
from src.infrastructure.security.password_hasher import hash_password


async def _ensure_user(
    session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    password: str,
    role: str,
) -> tuple[ApiUserModel, bool]:
    user = (
        await session.execute(select(ApiUserModel).where(ApiUserModel.email == email))
    ).scalar_one_or_none()
    created = user is None

    if user is None:
        user = ApiUserModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        session.add(user)
    else:
        user.tenant_id = tenant_id
        user.hashed_password = hash_password(password)
        user.role = role
        user.is_active = True

    return user, created


async def seed() -> None:
    configure_logging()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        tenant = (
            await session.execute(select(TenantModel).where(TenantModel.slug == "demo-corp"))
        ).scalar_one_or_none()
        tenant_created = tenant is None

        if tenant is None:
            tenant = TenantModel(
                id=uuid.uuid4(),
                name="Demo Corp",
                slug="demo-corp",
                is_active=True,
            )
            session.add(tenant)
        else:
            tenant.name = "Demo Corp"
            tenant.is_active = True

        await session.flush()

        _, admin_created = await _ensure_user(
            session,
            tenant_id=tenant.id,
            email="admin@demo.corp",
            password="admin1234!",
            role="admin",
        )
        _, viewer_created = await _ensure_user(
            session,
            tenant_id=tenant.id,
            email="viewer@demo.corp",
            password="viewer1234!",
            role="viewer",
        )

        await session.commit()
        print(f"✓ Tenant {'created' if tenant_created else 'updated'}: {tenant.id}")
        print(f"✓ Admin {'created' if admin_created else 'updated'}: admin@demo.corp / admin1234!")
        print(f"✓ Viewer {'created' if viewer_created else 'updated'}: viewer@demo.corp / viewer1234!")


if __name__ == "__main__":
    asyncio.run(seed())
