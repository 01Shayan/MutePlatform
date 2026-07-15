"""👥 Group Checker screen — offline Required Groups query over a workspace backup."""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.workspace import Workspace
from ...services.backup import format_duration
from ...services.group_checker import (
    BackupSource,
    GroupCheckerApplicationService,
    GroupCheckerOperationError,
    GroupCheckerResult,
    GroupQueryDescriptor,
    GroupQueryType,
    format_group_ids,
    parse_group_ids,
)
from .. import theme
from ..theme import Icon, console

_ACTIONS = [
    ("1", "Run Query"),
    ("0", "Back"),
]


def run(workspace: Workspace) -> None:
    service = GroupCheckerApplicationService()
    while True:
        theme.page(
            "Group Checker",
            theme.body_text(
                [
                    "Analyze user groups from an existing backup.",
                    "Find users missing required groups — offline, no panel access.",
                ]
            ),
            "",
            theme.option_menu(_ACTIONS),
            icon=Icon.GROUPS,
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
            _run_query_flow(service, workspace)


def _run_query_flow(service: GroupCheckerApplicationService, workspace: Workspace) -> None:
    backup = _select_backup(service, workspace)
    if backup is None:
        return

    theme.page(
        "Select Query",
        theme.body_text(["Choose a group-membership query."]),
        "",
        theme.option_menu([("1", "Required Groups"), ("0", "Back")]),
        icon=Icon.GROUPS,
    )
    choice = Prompt.ask(
        "\nSelect an option", choices=["1", "0"], default="0", show_choices=False
    )
    if choice == "0":
        return

    group_ids = _prompt_group_ids()
    if group_ids is None:
        return

    theme.page(
        "Query Confirmation",
        theme.info_panel(
            [
                ("Workspace", workspace.name),
                ("Backup", backup.name),
                ("Query", "Required Groups"),
                ("Required Groups", format_group_ids(group_ids)),
                ("Users in Backup", str(backup.users)),
            ]
        ),
        icon=Icon.GROUPS,
    )
    if not Confirm.ask("\nProceed?", default=True):
        theme.notify_info("Cancelled. No query was run.")
        theme.pause()
        return

    theme.clear()
    console.print(theme.page_header("Running Query", Icon.GROUPS))
    console.print()
    try:
        with console.status("[muted]Loading backup and running query…[/muted]", spinner="dots"):
            result = service.run_query(
                workspace,
                backup.name,
                GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, group_ids),
            )
    except GroupCheckerOperationError as exc:
        theme.page(
            "Query — Failed",
            theme.error_panel("Group Checker could not be completed", str(exc)),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return
    except Exception as exc:  # noqa: BLE001 — show friendly message, log is in the service
        theme.page(
            "Query — Failed",
            theme.error_panel("An unexpected error occurred.", str(exc)),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return

    _show_result(result)


def _select_backup(
    service: GroupCheckerApplicationService, workspace: Workspace
) -> BackupSource | None:
    sources = service.list_backups(workspace)
    if not sources:
        theme.page(
            "Select Backup",
            theme.body_text(["No backups have been created yet.", "Create a backup first."]),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return None

    items = [
        (str(index), source.name, f"{source.users} users · {source.size_label}")
        for index, source in enumerate(sources, start=1)
    ]
    theme.page(
        "Select Backup",
        theme.history_menu([*items, ("0", "Back")]),
        icon=Icon.GROUPS,
    )
    choice = Prompt.ask(
        "\nSelect a backup",
        choices=[item[0] for item in items] + ["0"],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return None
    return sources[int(choice) - 1]


def _prompt_group_ids() -> tuple[int, ...] | None:
    console.print()
    console.print(theme.section("Required Group IDs", Icon.GROUPS))
    console.print("[muted]Enter one or more group IDs, separated by commas or spaces (e.g. 1, 3).[/muted]")
    raw = Prompt.ask("\nGroup IDs", default="").strip()
    try:
        return parse_group_ids(raw)
    except ValueError as exc:
        theme.notify_warning(str(exc))
        theme.pause()
        return None


def _show_result(result: GroupCheckerResult) -> None:
    summary = theme.summary_panel(
        f"{Icon.SUCCESS} Query completed",
        [
            ("Backup", result.backup_name),
            ("Query", result.query_label),
            ("Required Groups", format_group_ids(result.required_group_ids)),
            ("Total Users", str(result.total_users)),
            ("Matching Users", str(result.matching_users)),
            ("Duration", format_duration(result.duration_seconds)),
        ],
        style="success",
    )

    if result.users:
        table = theme.data_table(["Username", "Current Groups", "Missing Groups"])
        for row in result.users:
            table.add_row(
                row.username,
                format_group_ids(row.current_group_ids),
                format_group_ids(row.missing_group_ids),
            )
        theme.page("Group Checker Result", summary, "", table, icon=Icon.GROUPS)
    else:
        theme.page(
            "Group Checker Result",
            summary,
            "",
            theme.body_text(["No users matched this query."]),
            icon=Icon.GROUPS,
        )
    theme.pause()
