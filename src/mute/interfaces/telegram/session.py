"""Small, in-memory navigation sessions keyed by Telegram chat."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Screen(str, Enum):
    HOME = "home"
    WORKSPACES = "workspaces"
    DASHBOARD = "dashboard"
    SETTINGS = "settings"
    ABOUT = "about"
    BACKUP = "backup"
    BACKUP_HISTORY = "backup-history"
    BACKUP_ARCHIVE_DETAIL = "backup-archive-detail"
    BACKUP_DELETE = "backup-delete"
    BACKUP_DELETE_SINGLE = "backup-delete-single"
    BACKUP_DELETE_CONFIRM = "backup-delete-confirm"
    BACKUP_DELETE_ALL_CONFIRM = "backup-delete-all-confirm"
    GROUP_CHECKER = "group-checker"
    GROUP_CHECKER_BACKUP = "group-checker-backup"
    GROUP_CHECKER_QUERY = "group-checker-query"
    GROUP_CHECKER_INPUT = "group-checker-input"
    GROUP_CHECKER_CONFIRM = "group-checker-confirm"
    GROUP_CHECKER_RESULT = "group-checker-result"
    GROUP_ENGINE_SELECT = "group-engine-select"
    GROUP_ENGINE_SELECT_BACKUP = "group-engine-select-backup"
    GROUP_ENGINE_SELECT_MODE = "group-engine-select-mode"
    GROUP_ENGINE_SELECT_NAMES = "group-engine-select-names"
    BULK_OPS = "bulk-ops"
    GROUP_MANAGER = "group-manager"
    GM_TARGET_MENU = "gm-target-menu"
    GM_TARGET_GROUPS = "gm-target-groups"
    GM_TARGET_REQUIRE = "gm-target-require"
    GM_TARGET_RULES = "gm-target-rules"
    GM_WORKING_SET = "gm-working-set"
    GM_ACTION_INPUT = "gm-action-input"
    GM_ACTION_CONFIRM = "gm-action-confirm"
    GM_REPORT = "gm-report"
    WS_ADD_NAME = "ws-add-name"
    WS_ADD_INTEGRATION = "ws-add-integration"
    WS_ADD_URL = "ws-add-url"
    WS_ADD_AUTH = "ws-add-auth"
    WS_ADD_USERNAME = "ws-add-username"
    WS_ADD_PASSWORD = "ws-add-password"
    WS_ADD_TOKEN = "ws-add-token"
    WS_ADD_SSL = "ws-add-ssl"
    WS_ADD_CONFIRM = "ws-add-confirm"
    WS_EDIT_NAME = "ws-edit-name"
    WS_EDIT_URL = "ws-edit-url"
    WS_EDIT_AUTH = "ws-edit-auth"
    WS_EDIT_USERNAME = "ws-edit-username"
    WS_EDIT_PASSWORD = "ws-edit-password"
    WS_EDIT_TOKEN = "ws-edit-token"
    WS_EDIT_SSL = "ws-edit-ssl"
    WS_EDIT_CONFIRM = "ws-edit-confirm"
    WS_DELETE_CONFIRM = "ws-delete-confirm"
    SETTINGS_RESET_TOKENS_CONFIRM = "settings-reset-tokens-confirm"
    SETTINGS_BOT_TOKEN_CONFIRM = "settings-bot-token-confirm"
    SETTINGS_BOT_TOKEN_INPUT = "settings-bot-token-input"
    SETTINGS_OWNER_CONFIRM = "settings-owner-confirm"
    SETTINGS_OWNER_INPUT = "settings-owner-input"


@dataclass
class TelegramSession:
    current_workspace: str | None = None
    current_screen: Screen = Screen.HOME
    current_action: str | None = None
    last_message_id: int | None = None
    draft: dict = field(default_factory=dict)
    temporary_messages: list[int] = field(default_factory=list)


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

    def clear_draft(self, chat_id: int) -> TelegramSession:
        session = self.get(chat_id)
        session.draft = {}
        return session

    def track_temporary(self, chat_id: int, message_id: int | None) -> TelegramSession:
        session = self.get(chat_id)
        if message_id is None:
            return session
        if message_id not in session.temporary_messages:
            session.temporary_messages.append(message_id)
        return session

    def clear_temporary(self, chat_id: int) -> TelegramSession:
        session = self.get(chat_id)
        session.temporary_messages = []
        return session

    def pop_temporary(self, chat_id: int) -> list[int]:
        session = self.get(chat_id)
        message_ids = list(session.temporary_messages)
        session.temporary_messages = []
        return message_ids
