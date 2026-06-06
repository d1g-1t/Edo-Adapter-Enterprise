from __future__ import annotations

import re


class INN:

    _LEGAL_WEIGHTS_1 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    _LEGAL_WEIGHTS_2 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    _INDIV_WEIGHTS_1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    _INDIV_WEIGHTS_2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

    def __init__(self, value: str) -> None:
        value = value.strip()
        if not re.fullmatch(r"\d{10}|\d{12}", value):
            raise ValueError(f"INN must be 10 or 12 digits, got: {value!r}")
        if not self._validate(value):
            raise ValueError(f"INN checksum invalid: {value!r}")
        self._value = value

    @staticmethod
    def _weighted(digits: list[int], weights: tuple[int, ...]) -> int:
        return sum(d * w for d, w in zip(digits, weights)) % 11 % 10

    def _validate(self, value: str) -> bool:
        digits = [int(c) for c in value]
        if len(digits) == 10:
            return digits[9] == self._weighted(digits[:9], self._LEGAL_WEIGHTS_1)
        c1 = self._weighted(digits[:10], self._INDIV_WEIGHTS_1)
        c2 = self._weighted(digits[:11], self._INDIV_WEIGHTS_2)
        return digits[10] == c1 and digits[11] == c2

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, INN) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"INN({self._value!r})"


class KPP:

    def __init__(self, value: str) -> None:
        value = value.strip()
        if not re.fullmatch(r"\d{9}", value):
            raise ValueError(f"KPP must be 9 digits, got: {value!r}")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, KPP) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
