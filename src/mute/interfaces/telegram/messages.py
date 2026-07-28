"""Shared Telegram message templates — Design System copy (mirrors CLI)."""

from __future__ import annotations

from ...core.constants import APP_NAME, DEVELOPER, FOOTER_TEXT, GITHUB_URL, TAGLINE, VERSION
from ...core.timefmt import relative_time
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService, WorkspaceNavigationItem
from ...services.backup import BackupArchive, BackupSummary, archive_display, format_duration, format_size
from ...services.bulk_operations.group_manager import (
    ExecutionReport,
    WorkingSet,
    format_duration_seconds,
    format_home_status,
    format_query_preview,
    format_review_screen,
)
from ...ui.copy import (
    ACTIONS_SECTION,
    BULK_OPS_INTRO,
    DIVIDER,
    MATCHED_TITLE,
    MENU_ABOUT,
    MENU_BACKUP_HISTORY,
    MENU_CHANGE_BOT_TOKEN,
    MENU_CHANGE_OWNER_IDS,
    MENU_DELETE_ALL,
    MENU_DELETE_BACKUP,
    MENU_DELETE_SINGLE,
    MENU_GROUP_MANAGER,
    MENU_MY_WORKSPACES,
    MENU_RESET_TOKENS,
    MENU_SETTINGS,
    MSG_BACKUP_DONE,
    MSG_SELECT_AT_LEAST_ONE_GROUP,
    PROMPT_BACKUP_INTERVAL,
    PROMPT_BACKUP_INTERVAL_EXAMPLE,
    PROMPT_MAX_BACKUPS,
    PROMPT_MAX_BACKUPS_EXAMPLE,
    REPORT_DURATION,
    REPORT_FAILED,
    REPORT_MATCHED,
    REPORT_SUCCESS,
    REPORT_SUMMARY_TITLE,
    REVIEW_TITLE,
    SETTINGS_INTRO,
    STATUS_COMPLETED,
    STATUS_EXECUTING,
    STATUS_FILTER_CLEARED,
    STATUS_GROUPS_LOADED,
    STATUS_MATCHED_RESET,
    STATUS_NO_CANCEL,
    STATUS_REFRESH_OK,
    STATUS_REFRESHING,
    STATUS_USERS_LOADED,
    TARGET_REQUIRE_ALL,
    TARGET_REQUIRE_ANY,
    TARGET_SELECT_GROUPS,
    TARGET_TITLE,
    TITLE_AUTO_BACKUP,
    TITLE_BACKUP,
    TITLE_BULK_OPS,
    TITLE_HOME,
    TITLE_MAX_BACKUPS,
    TITLE_SETTINGS,
)
from ...services.bulk_operations.group_manager.session import GroupManagerSession

_HOME_DIVIDER = DIVIDER


def home() -> str:
    """Home screen text — mirrors the CLI brand banner, menu, and footer."""
    return "\n".join(
        [
            f"🧠 {APP_NAME}",
            "",
            TAGLINE,
            "",
            "Current Version",
            f"v{VERSION}",
            "",
            _HOME_DIVIDER,
            "",
            TITLE_HOME,
            "",
            f"1. {MENU_MY_WORKSPACES}",
            f"2. {MENU_SETTINGS}",
            f"3. {MENU_ABOUT}",
            "",
            _HOME_DIVIDER,
            "",
            FOOTER_TEXT,
        ]
    )


def workspaces(items: list[WorkspaceNavigationItem]) -> str:
    lines = [MENU_MY_WORKSPACES, ""]
    if items:
        lines.extend(f"{index}. {item.name} — {item.panel}" for index, item in enumerate(items, start=1))
    else:
        lines.append("No workspaces yet. Choose Add Workspace to begin.")
    return "\n".join(lines)


def dashboard(workspace: WorkspaceNavigationItem) -> str:
    status = WorkspaceApplicationService.status_label(workspace.status)
    return f"{workspace.name}\n\nPanel: {workspace.panel}\nStatus: {status}"


def settings() -> str:
    return (
        f"{TITLE_SETTINGS}\n\n"
        f"{SETTINGS_INTRO}\n\n"
        f"1. {MENU_RESET_TOKENS}\n"
        f"2. {MENU_CHANGE_BOT_TOKEN}\n"
        f"3. {MENU_CHANGE_OWNER_IDS}"
    )


def about() -> str:
    return f"About\n\nPlatform: {APP_NAME}\nVersion: v{VERSION}\nDeveloper: {DEVELOPER}\nGitHub: {GITHUB_URL}"


def coming_next_phase() -> str:
    return "Coming in the next phase."


def status_label(status: ConnectionStatus) -> str:
    return WorkspaceApplicationService.status_label(status)


def backup_status(latest, *, workspace: str) -> str:
    """Render the Backup page status, mirroring the CLI's latest-backup panel."""
    header = f"{TITLE_BACKUP} — {workspace}"
    if latest is None:
        return f"{header}\n\nLatest Backup: No backup available.\nUsers: —\nArchive Size: —"
    return (
        f"{header}\n\n"
        f"Latest Backup: {relative_time(latest.created_at)}\n"
        f"({latest.created_at:%Y-%m-%d %H:%M:%S})\n"
        f"Users: {latest.users}\n"
        f"Archive Size: {format_size(latest.size_bytes)}"
    )


def auto_backup_status(workspace) -> str:
    from ...services.backup import format_auto_backup_lines

    return "\n".join(format_auto_backup_lines(workspace))


def max_backups_status(workspace) -> str:
    from ...services.backup import format_max_backups_lines

    return "\n".join(format_max_backups_lines(workspace))


def ask_backup_interval() -> str:
    return "\n".join(
        [
            TITLE_AUTO_BACKUP,
            "",
            PROMPT_BACKUP_INTERVAL,
            PROMPT_BACKUP_INTERVAL_EXAMPLE,
        ]
    )


def ask_max_backups() -> str:
    return "\n".join(
        [
            TITLE_MAX_BACKUPS,
            "",
            PROMPT_MAX_BACKUPS,
            PROMPT_MAX_BACKUPS_EXAMPLE,
        ]
    )


def backup_progress(stage: str) -> str:
    return f"{TITLE_BACKUP}\n\n{stage}"


def delete_menu() -> str:
    return (
        f"{MENU_DELETE_BACKUP}\n\n"
        f"1. {MENU_DELETE_SINGLE}\n"
        f"2. {MENU_DELETE_ALL}"
    )


def backup_result(summary: BackupSummary) -> str:
    return (
        f"{MSG_BACKUP_DONE}\n\n"
        f"Workspace: {summary.workspace}\n"
        f"Users: {summary.users}\n"
        f"Archive Size: {format_size(summary.size_bytes)}\n"
        f"Duration: {format_duration(summary.duration_seconds)}\n"
        f"Latest Backup: {summary.created_at:%Y-%m-%d %H:%M:%S}\n"
        f"Archive Name: {summary.archive_name}"
    )


def backup_history(
    archives: list[BackupArchive],
    *,
    title: str | None = None,
    selectable: bool = False,
) -> str:
    lines = [title or MENU_BACKUP_HISTORY, ""]
    if not archives:
        lines.append("No backups have been created yet.")
    else:
        lines.extend(f"{index}. {' — '.join(archive_display(archive))}" for index, archive in enumerate(archives, start=1))
        if selectable:
            lines.append("")
            lines.append("Select an archive to view details.")
    return "\n".join(lines)


def archive_details(workspace: str, archive: BackupArchive) -> str:
    name, created, size = archive_display(archive)
    lines = [
        "Archive Details",
        "",
        f"Workspace: {workspace}",
        f"Archive Name: {name}",
        f"Created Time: {created}",
        f"({archive.created_at:%Y-%m-%d %H:%M:%S})",
        f"Archive Size: {size}",
    ]
    if archive.users is not None:
        lines.append(f"User Count: {archive.users}")
    return "\n".join(lines)


def delete_single_confirmation(workspace: str, archive: BackupArchive) -> str:
    name, created, size = archive_display(archive)
    return f"Delete this backup?\n\nWorkspace: {workspace}\nArchive: {name}\nCreated: {created}\nSize: {size}\n\nThis action cannot be undone."


def delete_all_confirmation(workspace: str) -> str:
    return f"Delete ALL backups?\n\nWorkspace: {workspace}\n\nThis action cannot be undone."


def backup_error(detail: str | None = None) -> str:
    base = "Backup could not be completed."
    return f"{base}\n\n{detail}" if detail else f"{base} Please try again."


def no_backups_to_delete() -> str:
    return "No backup files to delete."


def friendly_error() -> str:
    return "Something went wrong. Please try again."


def bulk_ops_menu(workspace: str) -> str:
    return (
        f"{TITLE_BULK_OPS} — {workspace}\n\n"
        f"{BULK_OPS_INTRO}\n\n"
        f"1. {MENU_GROUP_MANAGER}"
    )


def gm_menu(workspace: str, *, session: GroupManagerSession | None = None) -> str:
    snapshot_users = session.snapshot.user_count if session and session.snapshot else 0
    groups = len(session.catalog) if session and session.catalog else 0
    working_set = session.working_set if session else None
    matched = working_set.matched if working_set is not None else None
    return "\n".join(
        format_home_status(
            workspace=workspace,
            snapshot_users=snapshot_users,
            available_groups=groups,
            working_set_matched=matched,
        )
    )


def gm_target_menu(*, rules_text: list[str] | None = None) -> str:
    lines = [TARGET_TITLE, "", "Who do you want to target?"]
    if rules_text:
        lines.extend(["", *rules_text])
    return "\n".join(lines)


def gm_group_selector(
    *,
    title: str,
    subtitle: str,
    groups,
    selected_ids: list[int] | None = None,
) -> str:
    """Shared Group Selector body — mirrors CLI format_group_selector_screen."""
    from ...ui.components.group_selector import build_group_state, format_group_selector_screen

    state = build_group_state(groups, selected=selected_ids or ())
    return "\n".join(
        format_group_selector_screen(title=title, subtitle=subtitle, state=state)
    )


def gm_target_groups(*, groups, selected_ids: list[int] | None = None) -> str:
    return gm_group_selector(
        title=TARGET_TITLE,
        subtitle=TARGET_SELECT_GROUPS,
        groups=groups,
        selected_ids=selected_ids,
    )


def gm_target_require() -> str:
    return "\n".join(
        [
            TARGET_TITLE,
            "",
            "Selected users should have:",
            "",
            f"(●) {TARGET_REQUIRE_ALL}",
            f"( ) {TARGET_REQUIRE_ANY}",
        ]
    )


def gm_target_rules_summary(rules_text: list[str]) -> str:
    return "\n".join([TARGET_TITLE, "", *rules_text])


def gm_working_set(working_set: WorkingSet, *, rules=None) -> str:
    lines = [MATCHED_TITLE, ""]
    lines.extend(format_query_preview(working_set, rules=rules))
    lines.extend(["", ACTIONS_SECTION])
    return "\n".join(lines)


def gm_review(working_set: WorkingSet, *, action_label: str, group_ids: tuple[int, ...], rules=None) -> str:
    lines = [REVIEW_TITLE, ""]
    lines.extend(
        format_review_screen(
            working_set, action_label=action_label, group_ids=group_ids, rules=rules
        )
    )
    return "\n".join(lines)


def gm_refresh_result() -> str:
    return "\n".join(
        [
            STATUS_REFRESHING,
            STATUS_USERS_LOADED,
            STATUS_GROUPS_LOADED,
            STATUS_REFRESH_OK,
            STATUS_FILTER_CLEARED,
            STATUS_MATCHED_RESET,
        ]
    )


def gm_operation_completed(report: ExecutionReport) -> str:
    return (
        f"{STATUS_COMPLETED}\n\n"
        f"{REPORT_SUMMARY_TITLE}\n"
        f"{REPORT_MATCHED}: {report.summary.matched}\n"
        f"{REPORT_SUCCESS}: {report.summary.success}\n"
        f"{REPORT_FAILED}: {report.summary.failed}\n"
        f"{REPORT_DURATION}: {format_duration_seconds(report.duration_ms)}"
    )


def gm_error(detail: str | None = None) -> str:
    base = "Group Manager could not complete the operation."
    return f"{base}\n\n{detail}" if detail else f"{base} Please try again."


def gm_invalid_ids(detail: str) -> str:
    return f"Invalid group IDs.\n\n{detail}\n\nSend numeric IDs again (e.g. 1, 3), or - for none."


def gm_running() -> str:
    return f"{STATUS_EXECUTING}\n\n{STATUS_NO_CANCEL}"


def gm_need_groups() -> str:
    return MSG_SELECT_AT_LEAST_ONE_GROUP


def ask_workspace_name(*, current: str | None = None) -> str:
    if current:
        return f"Edit Workspace\n\nCurrent name: {current}\n\nSend the new workspace name."
    return "Add Workspace\n\nSend the workspace name."


def ask_panel_url(*, current: str | None = None) -> str:
    hint = f"\nCurrent URL: {current}" if current else ""
    return f"Panel URL{hint}\n\nSend the panel base URL (https://…)."


def ask_username(*, current: str | None = None) -> str:
    hint = f"\nCurrent username: {current}" if current else ""
    return f"Username{hint}\n\nSend the panel username."


def ask_password(*, keep_allowed: bool = False) -> str:
    note = "\nSend a dash (-) to keep the current password." if keep_allowed else ""
    return f"Password{note}\n\nSend the panel password."


def ask_token(*, keep_allowed: bool = False) -> str:
    note = "\nSend a dash (-) to keep the current token." if keep_allowed else ""
    return f"Bearer Token{note}\n\nSend the panel bearer token."


def select_integration() -> str:
    return "Select Integration\n\nChoose the panel technology for this workspace."


def select_auth_method() -> str:
    return "Authentication Method\n\n1. Username / Password\n2. Bearer Token"


def select_verify_ssl(*, current: bool | None = None) -> str:
    hint = ""
    if current is not None:
        hint = f"\nCurrent: {'Yes' if current else 'No'}"
    return f"Verify TLS Certificate?{hint}"


def workspace_confirmation(draft: dict, *, title: str = "Create Workspace") -> str:
    auth = draft.get("auth", "password")
    auth_label = "Username / Password" if auth == "password" else "Bearer Token"
    lines = [
        title,
        "",
        f"Name: {draft.get('name', '—')}",
        f"Integration: {draft.get('integration_label', draft.get('integration', '—'))}",
        f"URL: {draft.get('base_url', '—')}",
        f"Authentication: {auth_label}",
    ]
    if auth == "password":
        lines.append(f"Username: {draft.get('username') or '—'}")
        lines.append(f"Password: {'••••••' if draft.get('password') else '—'}")
    else:
        lines.append(f"Token: {'••••••' if draft.get('token') else '—'}")
    lines.append(f"Verify SSL: {'Yes' if draft.get('verify_ssl', True) else 'No'}")
    if "probe_ok" in draft:
        lines.append("")
        lines.append("Connection: 🟢 Connected" if draft["probe_ok"] else "Connection: 🔴 Offline")
    return "\n".join(lines)


def workspace_created(name: str) -> str:
    return f"Workspace '{name}' created successfully."


def workspace_updated(name: str) -> str:
    return f"Workspace '{name}' updated successfully."


def workspace_deleted(name: str) -> str:
    return f"Workspace '{name}' deleted successfully."


def delete_workspace_confirmation(name: str) -> str:
    return (
        f"Delete Workspace\n\n"
        f"Workspace: {name}\n\n"
        "This action cannot be undone.\n\n"
        "Are you sure?"
    )


def workspace_error(detail: str) -> str:
    return f"Workspace operation failed.\n\n{detail}"


def reset_tokens_confirmation() -> str:
    return (
        "Reset Workspace Tokens\n\n"
        "This will remove all saved workspace tokens.\n\n"
        "Workspace configuration,\n"
        "passwords,\n"
        "backups\n"
        "and history\n"
        "will remain.\n\n"
        "Continue?"
    )


def reset_tokens_success(count: int) -> str:
    return "Workspace tokens removed successfully."


def change_bot_token_confirmation() -> str:
    return (
        "Change Bot Token\n\n"
        "You will be asked for a new BOT_TOKEN.\n"
        "Restart the bot after saving to apply the change.\n\n"
        "Continue?"
    )


def ask_bot_token() -> str:
    return "Change Bot Token\n\nSend the new Telegram bot token from @BotFather."


def bot_token_updated() -> str:
    return "Bot token updated successfully.\n\nRestart the bot to apply the changes."


def change_owner_ids_confirmation() -> str:
    return (
        "Change Owner IDs\n\n"
        "You will be asked for one or more Telegram owner IDs.\n"
        "Restart the bot after saving to apply the change.\n\n"
        "Continue?"
    )


def ask_owner_ids() -> str:
    return (
        "Change Owner IDs\n\n"
        "Send one or more numeric Telegram user IDs.\n"
        "Example: 123456789\n"
        "Or: 123456789,987654321"
    )


def owner_ids_updated(owner_ids: list[int]) -> str:
    joined = ", ".join(str(value) for value in owner_ids)
    return f"Owner IDs updated successfully.\n\nOwner IDs: {joined}\n\nRestart the bot to apply the changes."


def settings_error(detail: str) -> str:
    return f"Settings update failed.\n\n{detail}"


def verifying_connection() -> str:
    return "Verifying connection…"
