from __future__ import annotations

from typing import Any

from src.application.interfaces.i_edo_provider import IEDOProvider
from src.domain.value_objects.provider_type import ProviderType
from src.infrastructure.providers.stub.stub_provider import StubEDOProvider


class ProviderFactory:

    @staticmethod
    def create(
        provider_type: ProviderType,
        credentials: dict[str, Any],
    ) -> IEDOProvider:
        if provider_type == ProviderType.STUB:
            return StubEDOProvider(credentials=credentials)

        if provider_type == ProviderType.DIADOC:
            from src.infrastructure.providers.diadoc.diadoc_provider import DiadocProvider
            return DiadocProvider(credentials=credentials)

        if provider_type == ProviderType.SBIS:
            from src.infrastructure.providers.sbis.sbis_provider import SBISProvider
            return SBISProvider(credentials=credentials)

        if provider_type == ProviderType.KONTUR_EDO:
            from src.infrastructure.providers.kontur_edo.kontur_provider import KonturEDOProvider
            return KonturEDOProvider(credentials=credentials)

        raise ValueError(f"Unsupported provider type: {provider_type}")
