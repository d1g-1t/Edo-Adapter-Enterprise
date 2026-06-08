from __future__ import annotations

from enum import StrEnum


class ProviderType(StrEnum):
    DIADOC = "DIADOC"
    SBIS = "SBIS"
    KONTUR_EDO = "KONTUR_EDO"
    STUB = "STUB"
