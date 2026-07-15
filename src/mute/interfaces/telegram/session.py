"""Small, in-memory navigation sessions keyed by Telegram chat."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Screen(str, Enum):
    HOME = "home"
    WORKSPACES = "workspaces"
    DASHBOARD = "dashboard"
    SETTINGS = "settings"
    ABOUT = "about"
    BACKUP = "backup"
    BACKUP_HISTORY = "backup-history"
    BACKUP_DELETE = "backup-delete"
    BACKUP_DELETE_SINGLE = "backup-delete-single"
    BACKUP_DELETE_CONFIRM = "backup-delete-confirm"
    BACKUP_DELETE_ALL_CONFIRM = "backup-delete-all-confirm"


@dataclass
class TelegramSession:
    current_workspace: str | None = None
    current_screen: Screen = Screen.HOME
    current_action: str | None = None
    last_message_id: int | None = None


class SessionManager:
    """Keeps one ephemeral session per chat; no data is persisted."""

    def __init__(self) -> None:
        self._sessions: dict[int, TelegramSession] = {}

    def get(self, chat_id: int) -> TelegramSession:
        return self._sessions.setdefault(chat_id, TelegramSession())

    def navigate(
        self, chat_id: int, screen: Screen, *, action: str | None = None
    ) -> TelegramSession:
        session = self.get(chat_id)
        session.current_screen = screen
        session.current_action = action
        return session

    def clear(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)

    def remember_message(self, chat_id: int, message_id: int | None) -> TelegramSession:
        session = self.get(chat_id)
        session.last_message_id = message_id
        return session
