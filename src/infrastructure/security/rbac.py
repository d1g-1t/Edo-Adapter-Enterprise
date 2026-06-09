from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


_ADMIN_VERBS = frozenset(
    [
        "provider_accounts:create",
        "provider_accounts:delete",
        "provider_accounts:activate",
        "provider_accounts:deactivate",
        "documents:send",
        "documents:retry",
        "dlq:replay",
        "dlq:read",
        "incoming:poll",
        "providers:read",
        "audit:read",
    ]
)

_VIEWER_VERBS = frozenset(
    [
        "provider_accounts:read",
        "documents:read",
        "incoming:read",
        "providers:read",
        "audit:read",
    ]
)

_ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.ADMIN: _ADMIN_VERBS | _VIEWER_VERBS,
    Role.VIEWER: _VIEWER_VERBS,
}


def has_permission(role: str, verb: str) -> bool:
    try:
        r = Role(role)
    except ValueError:
        return False
    return verb in _ROLE_PERMISSIONS.get(r, frozenset())


def assert_permission(role: str, verb: str) -> None:
    if not has_permission(role, verb):
        raise PermissionError(f"Role '{role}' is not allowed to '{verb}'")
