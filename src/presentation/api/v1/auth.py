from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from src.core.security import create_access_token, create_refresh_token, decode_token
from src.infrastructure.database.models import ApiUserModel
from src.presentation.deps import AuthUser, DBSession

router = APIRouter(prefix="/auth", tags=["auth"])
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    stmt = select(ApiUserModel).where(
        ApiUserModel.email == body.email,
        ApiUserModel.is_active.is_(True),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not _pwd_ctx.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    extra = {"tenant_id": str(user.tenant_id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra=extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DBSession) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expected refresh token")

    user_id = uuid.UUID(str(payload["sub"]))
    user = (
        await db.execute(
            select(ApiUserModel).where(ApiUserModel.id == user_id, ApiUserModel.is_active.is_(True))
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    extra = {"tenant_id": str(user.tenant_id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra=extra),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: AuthUser, db: DBSession) -> UserResponse:
    user = (
        await db.execute(select(ApiUserModel).where(ApiUserModel.id == current_user.user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
    )
