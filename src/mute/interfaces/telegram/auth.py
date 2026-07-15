"""Owner-only authorization for Telegram updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update


@dataclass(frozen=True)
class OwnerAuthorization:
    """Authorizes only the configured Telegram user IDs."""

    owner_ids: frozenset[int]

    def allows(self, telegram_id: int | None) -> bool:
        return telegram_id is not None and telegram_id in self.owner_ids

    def allows_update(self, update: "Update") -> bool:
        user = update.effective_user
        return self.allows(user.id if user is not None else None)
