"""Telegram / application settings operations shared by all interfaces."""

from __future__ import annotations

from ...core.config import save_bot_token, save_telegram_config, telegram_settings


class SettingsOperationError(Exception):
    """A safe, interface-ready explanation of a settings failure."""


class SettingsApplicationService:
    """Persist Telegram secrets and owner IDs without exposing raw config I/O to interfaces."""

    def update_bot_token(self, token: str) -> None:
        cleaned = (token or "").strip()
        if not cleaned:
            raise SettingsOperationError("Bot token cannot be empty.")
        if ":" not in cleaned:
            raise SettingsOperationError("Bot token looks invalid. Paste the full token from @BotFather.")
        save_bot_token(cleaned)

    def update_owner_ids(self, raw: str) -> list[int]:
        owner_ids = self.parse_owner_ids(raw)
        if not owner_ids:
            raise SettingsOperationError("Enter at least one numeric Telegram owner ID.")
        current = telegram_settings()
        save_telegram_config(enabled=current.enabled, owner_ids=owner_ids)
        return owner_ids

    @staticmethod
    def parse_owner_ids(raw: str) -> list[int]:
        """Parse comma/space-separated Telegram user IDs. Returns [] when any token is invalid."""
        owner_ids: list[int] = []
        for chunk in (raw or "").replace(",", " ").split():
            try:
                owner_ids.append(int(chunk))
            except ValueError:
                return []
        # Deduplicate while preserving order.
        seen: set[int] = set()
        unique: list[int] = []
        for value in owner_ids:
            if value not in seen:
                seen.add(value)
                unique.append(value)
        return unique
