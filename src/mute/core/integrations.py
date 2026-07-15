"""Supported integrations.

Mute is a platform; an *integration* is one VPN panel technology (PasarGuard
today; Marzban, Hiddify, Xray, … in the future). A workspace is bound to exactly one
integration, which determines the API implementation used at runtime.

Adding a future integration is a one-line entry here plus its ``integrations/<key>/`` package.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Integration:
    key: str
    name: str
    icon: str
    available: bool = False  # True once a real API implementation exists


INTEGRATIONS: tuple[Integration, ...] = (
    Integration(key="pasarguard", name="PasarGuard", icon="🛡", available=True),
    Integration(key="marzban", name="Marzban", icon="🟣"),
    Integration(key="hiddify", name="Hiddify", icon="🟢"),
    Integration(key="xray", name="Xray", icon="⚡"),
)


def list_integrations() -> tuple[Integration, ...]:
    return INTEGRATIONS


def get_integration(key: str) -> Integration | None:
    return next((it for it in INTEGRATIONS if it.key == key), None)


def integration_name(key: str) -> str:
    """Display name for an integration key, falling back to the key itself."""
    integration = get_integration(key)
    return integration.name if integration else key


def resolve_integration_key(value: str) -> str:
    """Resolve a stored integration value (key or display name) back to its canonical key."""
    if get_integration(value) is not None:
        return value
    for integration in INTEGRATIONS:
        if integration.name.lower() == value.lower():
            return integration.key
    return value
