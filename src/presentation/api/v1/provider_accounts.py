from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from src.application.dto import (
    ProviderAccountResponse,
    RegisterProviderAccountRequest,
)
from src.domain.entities.provider_account import ProviderAccount
from src.domain.value_objects.provider_type import ProviderType
from src.infrastructure.database.repositories import SQLProviderAccountRepository
from src.presentation.deps import AdminUser, AuthUser, DBSession

router = APIRouter(prefix="/provider-accounts", tags=["provider-accounts"])


def _to_response(account: ProviderAccount) -> ProviderAccountResponse:
    return ProviderAccountResponse(
        id=account.id,
        tenant_id=account.tenant_id,
        provider_type=account.provider_type.value,
        account_name=account.account_name,
        is_active=account.is_active,
        priority=account.priority,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.post("/", response_model=ProviderAccountResponse, status_code=status.HTTP_201_CREATED)
async def register_provider_account(
    body: RegisterProviderAccountRequest,
    current_user: AdminUser,
    db: DBSession,
) -> ProviderAccountResponse:
    repo = SQLProviderAccountRepository(db)
    account = ProviderAccount.create(
        tenant_id=current_user.tenant_id,
        provider_type=ProviderType(body.provider_type),
        account_name=body.account_name,
        credentials_json=body.credentials_json,
        webhook_secret=body.webhook_secret,
        rate_limit_per_minute=body.rate_limit_per_minute,
        priority=body.priority,
    )
    await repo.save(account)
    return _to_response(account)


@router.get("/", response_model=list[ProviderAccountResponse])
async def list_provider_accounts(
    current_user: AuthUser,
    db: DBSession,
    active_only: bool = True,
) -> list[ProviderAccountResponse]:
    repo = SQLProviderAccountRepository(db)
    accounts = await repo.list_by_tenant(current_user.tenant_id, active_only=active_only)
    return [_to_response(a) for a in accounts]


@router.get("/{account_id}", response_model=ProviderAccountResponse)
async def get_provider_account(
    account_id: uuid.UUID,
    current_user: AuthUser,
    db: DBSession,
) -> ProviderAccountResponse:
    repo = SQLProviderAccountRepository(db)
    account = await repo.get_by_id(account_id)
    if not account or account.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return _to_response(account)


@router.post("/{account_id}/activate", response_model=ProviderAccountResponse)
async def activate_account(
    account_id: uuid.UUID,
    current_user: AdminUser,
    db: DBSession,
) -> ProviderAccountResponse:
    repo = SQLProviderAccountRepository(db)
    account = await repo.get_by_id(account_id)
    if not account or account.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    account.activate()
    await repo.update(account)
    return _to_response(account)


@router.post("/{account_id}/deactivate", response_model=ProviderAccountResponse)
async def deactivate_account(
    account_id: uuid.UUID,
    current_user: AdminUser,
    db: DBSession,
) -> ProviderAccountResponse:
    repo = SQLProviderAccountRepository(db)
    account = await repo.get_by_id(account_id)
    if not account or account.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    account.deactivate()
    await repo.update(account)
    return _to_response(account)
