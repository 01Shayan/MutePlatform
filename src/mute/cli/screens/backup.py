"""📦 Backup screen — the first implementation of the Job Lifecycle.

The menu label is "Backup", but the workflow uses the more accurate verb "Export". All data
is read from and written to the active **workspace**.
"""

from __future__ import annotations

from rich.prompt import Prompt

from ...core.timefmt import relative_time
from ...core.workspace import Workspace
from ...services.backup import BackupApplicationService, BackupOperationError, archive_display, format_duration, format_size
from ...services.workspace import ConnectionStatus, WorkspaceApplicationService
from ...ui.copy import (
    BTN_BACK,
    MENU_BACKUP_HISTORY,
    MENU_CREATE_EXPORT,
    MENU_DELETE_ALL,
    MENU_DELETE_BACKUP,
    MENU_DELETE_SINGLE,
    TITLE_BACKUP,
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
    ("2", MENU_BACKUP_HISTORY),
    ("3", MENU_DELETE_BACKUP),
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
            _browse_backups(workspace)
        elif choice == "3":
            _delete_menu(workspace)
