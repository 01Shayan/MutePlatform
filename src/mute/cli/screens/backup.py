"""📦 Backup screen — Create Export, Auto Backup, Max Backups, History, Delete.

All data is read from and written to the active **workspace**. Manual and Auto Backup
share :meth:`BackupApplicationService.create_export` (create + retention cleanup).
"""

from __future__ import annotations

from rich.prompt import Prompt

from ...core.timefmt import relative_time
from ...core.workspace import Workspace
from ...services.backup import (
    BackupApplicationService,
    BackupOperationError,
    archive_display,
    format_auto_backup_lines,
    format_duration,
    format_max_backups_lines,
    format_size,
    parse_auto_backup_interval,
    parse_max_backups,
)
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService
from ...ui.copy import (
    BTN_BACK,
    BTN_CHANGE_INTERVAL,
    BTN_CHANGE_LIMIT,
    BTN_DISABLE,
    BTN_ENABLE,
    MENU_AUTO_BACKUP,
    MENU_BACKUP_HISTORY,
    MENU_CREATE_EXPORT,
    MENU_DELETE_ALL,
    MENU_DELETE_BACKUP,
    MENU_DELETE_SINGLE,
    MENU_MAX_BACKUPS,
    MSG_INVALID_INTERVAL,
    MSG_INVALID_MAX_BACKUPS,
    PROMPT_BACKUP_INTERVAL,
    PROMPT_BACKUP_INTERVAL_EXAMPLE,
    PROMPT_MAX_BACKUPS,
    PROMPT_MAX_BACKUPS_EXAMPLE,
    TITLE_AUTO_BACKUP,
    TITLE_BACKUP,
    TITLE_MAX_BACKUPS,
)
from .. import theme
from ..job import Job, JobError, JobOutcome, ProgressReporter, run_job
from ..theme import Icon


class BackupJob(Job):
    icon = Icon.BACKUP
    title = TITLE_BACKUP
    action = "Export"
    prepare_message = "Connecting…"
    description = [
        "Export panel data into a clean backup file.",
        "Only the required operational information is exported.",
        "Sensitive data such as proxy settings, UUIDs and private keys are excluded.",
    ]

    def __init__(self) -> None:
        self._service = BackupApplicationService()

    def prepare(self, workspace: Workspace) -> list[tuple[str, str]]:
        try:
            rows = self._service.prepare_export(workspace)
        except BackupOperationError as exc:
            WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
            raise JobError(str(exc)) from exc
        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.CONNECTED)
        return rows

    def execute(self, workspace: Workspace, report: ProgressReporter) -> JobOutcome:
        try:
            result = self._service.create_export(workspace, progress=report)
        except BackupOperationError:
            WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.OFFLINE)
            raise
        WorkspaceApplicationService.record_connection_status(workspace, ConnectionStatus.CONNECTED)

        rows = [
            ("Workspace", workspace.name),
            ("Users", str(result.users)),
            ("Archive Size", format_size(result.size_bytes)),
            ("Duration", format_duration(result.duration_seconds)),
            ("Latest Backup", result.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("Archive Name", result.archive_name),
        ]
        return JobOutcome(
            f"{Icon.SUCCESS} Export completed successfully",
            rows,
            style="success",
        )


_ACTIONS = [
    ("1", MENU_CREATE_EXPORT),
    ("2", MENU_AUTO_BACKUP),
    ("3", MENU_MAX_BACKUPS),
    ("4", MENU_BACKUP_HISTORY),
    ("5", MENU_DELETE_BACKUP),
    ("0", BTN_BACK),
]

_DELETE_MENU = [
    ("1", MENU_DELETE_SINGLE),
    ("2", MENU_DELETE_ALL),
    ("0", BTN_BACK),
]


def _history_items(workspace: Workspace) -> list[tuple]:
    """Build numbered history menu entries (newest first), excluding the Back option."""
    service = BackupApplicationService()
    return [
        (str(index), *archive_display(archive))
        for index, archive in enumerate(service.archives(workspace), start=1)
    ]


def _browse_backups(workspace: Workspace) -> None:
    items = _history_items(workspace)
    if not items:
        theme.page(MENU_BACKUP_HISTORY, theme.body_text(["No backups have been created yet."]))
        theme.pause()
        return

    theme.page(MENU_BACKUP_HISTORY, theme.history_menu([*items, ("0", BTN_BACK)]))
    Prompt.ask(
        "\nSelect an option",
        choices=[item[0] for item in items] + ["0"],
        default="0",
        show_choices=False,
    )


def _confirm_yes_no(title: str, *body: object) -> bool:
    theme.page(title, *body, "", theme.option_menu([("1", "Yes"), ("0", "No")]))
    return (
        Prompt.ask("\nSelect an option", choices=["1", "0"], default="0", show_choices=False)
        == "1"
    )


def _delete_single_backup(workspace: Workspace) -> None:
    service = BackupApplicationService()
    archives = service.archives(workspace)
    if not archives:
        theme.notify_warning("No backup files to delete.")
        return

    items = _history_items(workspace)
    theme.page(MENU_DELETE_BACKUP, theme.history_menu([*items, ("0", BTN_BACK)]))
    choices = [item[0] for item in items] + ["0"]
    choice = Prompt.ask(
        "\nSelect a backup to delete",
        choices=choices,
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return

    target = archives[int(choice) - 1]

    if not _confirm_yes_no(
        f"{Icon.WARNING} Delete this backup?",
        theme.info_panel(
            [
                ("Workspace", workspace.name),
                ("File", target.path.name),
                ("Created", archive_display(target)[1]),
                ("Size", archive_display(target)[2]),
                ("", "This action cannot be undone."),
            ]
        ),
    ):
        theme.notify_info("Cancelled. Nothing was deleted.")
        return

    service.delete_archive(workspace, target)
    theme.notify_success(f"{Icon.SUCCESS} Backup deleted successfully.")


def _delete_menu(workspace: Workspace) -> None:
    while True:
        theme.page(MENU_DELETE_BACKUP, theme.option_menu(_DELETE_MENU))
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[item[0] for item in _DELETE_MENU],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return
        if choice == "1":
            _delete_single_backup(workspace)
            return
        if choice == "2":
            _delete_all_backups(workspace)
            return


def _delete_all_backups(workspace: Workspace) -> None:
    service = BackupApplicationService()
    if not service.archives(workspace) and service.latest(workspace) is None:
        theme.notify_warning("No backup files to delete.")
        return

    if not _confirm_yes_no(
        f"{Icon.WARNING} Delete ALL backup files for this workspace?",
        theme.info_panel(
            [
                ("Workspace", workspace.name),
                ("", "This action cannot be undone."),
            ]
        ),
    ):
        theme.notify_info("Cancelled. Nothing was deleted.")
        return

    service.delete_all_archives(workspace)
    theme.notify_success(f"{Icon.SUCCESS} All backup files deleted successfully.")


def _ask_interval() -> int | None:
    theme.page(
        TITLE_AUTO_BACKUP,
        theme.body_text([PROMPT_BACKUP_INTERVAL, "", PROMPT_BACKUP_INTERVAL_EXAMPLE]),
    )
    raw = Prompt.ask("\nInterval", default="").strip()
    if not raw:
        return None
    try:
        return parse_auto_backup_interval(raw)
    except ValueError:
        theme.notify_error(MSG_INVALID_INTERVAL)
        theme.pause()
        return None


def _ask_max_backups() -> int | None:
    theme.page(
        TITLE_MAX_BACKUPS,
        theme.body_text([PROMPT_MAX_BACKUPS, "", PROMPT_MAX_BACKUPS_EXAMPLE]),
    )
    raw = Prompt.ask("\nLimit", default="").strip()
    if not raw:
        return None
    try:
        return parse_max_backups(raw)
    except ValueError:
        theme.notify_error(MSG_INVALID_MAX_BACKUPS)
        theme.pause()
        return None


def _auto_backup_menu(workspace: Workspace) -> Workspace:
    workspaces = WorkspaceApplicationService.for_navigation()
    while True:
        # Reload so CLI sees the latest persisted settings.
        current = workspaces.workspace(workspace.name) or workspace
        enabled = bool(current.auto_backup_enabled)
        actions = (
            [("1", BTN_CHANGE_INTERVAL), ("2", BTN_DISABLE), ("0", BTN_BACK)]
            if enabled
            else [("1", BTN_ENABLE), ("0", BTN_BACK)]
        )
        theme.page(
            TITLE_AUTO_BACKUP,
            theme.body_text(format_auto_backup_lines(current)[1:]),
            "",
            theme.option_menu(actions),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[item[0] for item in actions],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return current
        if not enabled and choice == "1":
            interval = _ask_interval()
            if interval is None:
                continue
            current = workspaces.save_backup_settings(
                current, auto_backup_enabled=True, auto_backup_interval=interval
            )
            continue
        if enabled and choice == "1":
            interval = _ask_interval()
            if interval is None:
                continue
            current = workspaces.save_backup_settings(current, auto_backup_interval=interval)
            continue
        if enabled and choice == "2":
            current = workspaces.save_backup_settings(current, auto_backup_enabled=False)
            continue


def _max_backups_menu(workspace: Workspace) -> Workspace:
    workspaces = WorkspaceApplicationService.for_navigation()
    while True:
        current = workspaces.workspace(workspace.name) or workspace
        theme.page(
            TITLE_MAX_BACKUPS,
            theme.body_text(format_max_backups_lines(current)[1:]),
            "",
            theme.option_menu([("1", BTN_CHANGE_LIMIT), ("0", BTN_BACK)]),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=["1", "0"],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return current
        limit = _ask_max_backups()
        if limit is None:
            continue
        current = workspaces.save_backup_settings(current, max_backups=limit)
        BackupApplicationService().enforce_retention(current)


def _status_panel(workspace: Workspace):
    latest = BackupApplicationService().latest(workspace)
    if latest is None:
        return theme.summary_panel(
            "Latest Backup",
            [
                ("Latest Backup", "No backup available."),
                ("Users", "—"),
                ("Archive Size", "—"),
            ],
            style="warning",
        )
    return theme.summary_panel(
        "Latest Backup",
        [
            ("Latest Backup", relative_time(latest.created_at)),
            ("", latest.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("Users", str(latest.users)),
            ("Archive Size", format_size(latest.size_bytes)),
        ],
        style="info",
    )


def run(workspace: Workspace) -> None:
    while True:
        theme.page(
            TITLE_BACKUP,
            _status_panel(workspace),
            "",
            theme.option_menu(_ACTIONS),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[item[0] for item in _ACTIONS],
            default="0",
            show_choices=False,
        )

        if choice == "0":
            return
        if choice == "1":
            run_job(BackupJob(), workspace)
        elif choice == "2":
            workspace = _auto_backup_menu(workspace)
        elif choice == "3":
            workspace = _max_backups_menu(workspace)
        elif choice == "4":
            _browse_backups(workspace)
        elif choice == "5":
            _delete_menu(workspace)
