"""Typed models for PasarGuard API payloads.

Models keep the fields the application actually reasons about while preserving the full
raw payload (``raw``) so backups stay lossless and future features can access any field
without a model change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Token:
    """Bearer token returned by ``/api/admin/token``."""

    access_token: str
    token_type: str = "bearer"

    @classmethod
    def from_dict(cls, data: dict) -> "Token":
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
        )


@dataclass
class User:
    """A PasarGuard user. ``raw`` holds the complete payload for lossless backups."""

    username: str
    status: str | None = None
    group_ids: list[int] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            username=data.get("username", ""),
            status=data.get("status"),
            group_ids=list(data.get("group_ids") or []),
            raw=data,
        )
