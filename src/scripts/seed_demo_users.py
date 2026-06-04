from __future__ import annotations

import asyncio
import uuid

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.logging import configure_logging
from src.infrastructure.database.models import ApiUserModel, TenantModel
from src.infrastructure.database.session import engine

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed() -> None:
    configure_logging()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        # Tenant
        tenant = TenantModel(
            id=uuid.uuid4(),
            name="Demo Corp",
            slug="demo-corp",
            is_active=True,
        )
        session.add(tenant)

        # Admin user
        admin = ApiUserModel(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="admin@demo.corp",
            hashed_password=_pwd.hash("admin1234!"),
            role="admin",
            is_active=True,
        )
        session.add(admin)

        viewer = ApiUserModel(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="viewer@demo.corp",
            hashed_password=_pwd.hash("viewer1234!"),
            role="viewer",
            is_active=True,
        )
        session.add(viewer)

        await session.commit()
        print(f"✓ Tenant: {tenant.id}")
        print(f"✓ Admin: admin@demo.corp / admin1234!")
        print(f"✓ Viewer: viewer@demo.corp / viewer1234!")


if __name__ == "__main__":
    asyncio.run(seed())
