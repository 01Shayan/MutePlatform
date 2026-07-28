"""Interface-only navigation coordinator for Telegram screens."""

from __future__ import annotations

from .session import Screen, SessionManager, TelegramSession


class Router:
    def __init__(self, sessions: SessionManager) -> None:
        self._sessions = sessions

    def session(self, chat_id: int) -> TelegramSession:
        """Return the current session for a chat without navigating."""
        return self._sessions.get(chat_id)

    def go_to(
        self, chat_id: int, screen: Screen, *, action: str | None = None
    ) -> TelegramSession:
        return self._sessions.navigate(chat_id, screen, action=action)

    def home(self, chat_id: int) -> TelegramSession:
        session = self.go_to(chat_id, Screen.HOME)
        session.current_workspace = None
        return session

    def workspaces(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.WORKSPACES)

    def dashboard(self, chat_id: int, workspace_name: str) -> TelegramSession:
        session = self.go_to(chat_id, Screen.DASHBOARD)
        session.current_workspace = workspace_name
        return session

    def settings(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.SETTINGS)

    def about(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.ABOUT)

    def back(self, chat_id: int) -> TelegramSession:
        session = self._sessions.get(chat_id)
        if session.current_screen is Screen.DASHBOARD:
            session.current_workspace = None
            return self.workspaces(chat_id)
        return self.home(chat_id)

    def backup(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP)

    def backup_history(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_HISTORY)

    def backup_archive_detail(self, chat_id: int, archive_name: str) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_ARCHIVE_DETAIL, action=archive_name)

    def backup_delete(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_DELETE)

    def backup_delete_single(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_DELETE_SINGLE)

    def backup_delete_confirmation(self, chat_id: int, archive_name: str) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_DELETE_CONFIRM, action=f"delete:{archive_name}")

    def backup_delete_all_confirmation(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_DELETE_ALL_CONFIRM, action="delete-all")

    def backup_auto(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_AUTO)

    def backup_auto_interval(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_AUTO_INTERVAL)

    def backup_max(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_MAX)

    def backup_max_input(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BACKUP_MAX_INPUT)

    def bulk_ops(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.BULK_OPS)

    def group_manager(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GROUP_MANAGER)

    def gm_target_menu(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_TARGET_MENU)

    def gm_target_groups(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_TARGET_GROUPS)

    def gm_target_require(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_TARGET_REQUIRE)

    def gm_target_rules(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_TARGET_RULES)

    def gm_working_set(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_WORKING_SET)

    def gm_action_input(self, chat_id: int, action_id: str) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_ACTION_INPUT, action=action_id)

    def gm_action_confirm(self, chat_id: int, action_id: str) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_ACTION_CONFIRM, action=action_id)

    def gm_report(self, chat_id: int) -> TelegramSession:
        return self.go_to(chat_id, Screen.GM_REPORT)

    def remember_message(self, chat_id: int, message_id: int | None) -> TelegramSession:
        return self._sessions.remember_message(chat_id, message_id)

    def clear_draft(self, chat_id: int) -> TelegramSession:
        return self._sessions.clear_draft(chat_id)

    def track_temporary(self, chat_id: int, message_id: int | None) -> TelegramSession:
        return self._sessions.track_temporary(chat_id, message_id)

    def clear_temporary(self, chat_id: int) -> TelegramSession:
        return self._sessions.clear_temporary(chat_id)

    def pop_temporary(self, chat_id: int) -> list[int]:
        return self._sessions.pop_temporary(chat_id)
