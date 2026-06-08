from __future__ import annotations

from fastapi import APIRouter

from src.domain.value_objects.provider_type import ProviderType
from src.presentation.deps import AuthUser

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/types")
async def list_provider_types(current_user: AuthUser) -> list[dict[str, str]]:
    return [
        {
            "id": pt.value,
            "name": _display_name(pt),
            "description": _description(pt),
        }
        for pt in ProviderType
    ]


def _display_name(pt: ProviderType) -> str:
    return {
        ProviderType.DIADOC: "Диадок (СКБ Контур)",
        ProviderType.SBIS: "СБИС (Тензор)",
        ProviderType.KONTUR_EDO: "Контур.ЭДО",
        ProviderType.STUB: "Stub (для разработки)",
    }[pt]


def _description(pt: ProviderType) -> str:
    return {
        ProviderType.DIADOC: "Интеграция с Диадок через REST API с PASETO-токенами",
        ProviderType.SBIS: "Интеграция с СБИС через JSON-RPC API",
        ProviderType.KONTUR_EDO: "Интеграция с Контур.ЭДО через REST API",
        ProviderType.STUB: "In-process заглушка для tests и local dev",
    }[pt]
