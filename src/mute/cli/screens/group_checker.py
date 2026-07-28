"""👥 Group Engine screen — central entry for all group operations.

Check reuses the existing offline Required Groups query. Write operations use the
shared Group Engine session and pipeline; Add / Remove / Replace remain Coming Soon
plugins until their business logic is implemented.
"""

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
from ...services.group_engine import (
    GroupEngineApplicationService,
    GroupEngineError,
    GroupEngineSession,
)
from .. import theme
from ..theme import Icon, console
from . import placeholder

_ACTIONS = [
    ("1", "Check"),
    ("2", "Select Users"),
    ("3", "Add"),
    ("4", "Remove"),
    ("5", "Replace"),
    ("6", "History"),
    ("0", "Back"),
]

_WRITE_OPS = {
    "3": "add",
    "4": "remove",
    "5": "replace",
}


def run(workspace: Workspace) -> None:
    checker = GroupCheckerApplicationService()
    engine = GroupEngineApplicationService()
    engine.begin_session(workspace)
    try:
        while True:
            session = engine.require_session()
            theme.page(
                "Group Engine",
                theme.body_text(_engine_intro(session)),
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
                _run_check_flow(checker, workspace)
            elif choice == "2":
                _select_users_flow(engine, checker, workspace)
            elif choice in _WRITE_OPS:
                _write_operation_placeholder(engine, _WRITE_OPS[choice])
            elif choice == "6":
                placeholder.coming_soon(
                    Icon.GROUPS,
                    "History",
                    ["Review metadata for past group operations in this workspace."],
                )
    finally:
        engine.leave_session()


def _engine_intro(session: GroupEngineSession) -> list[str]:
    lines = [
        "Central home for all group operations.",
        "Write ops share one session: Select Users → Operation → Preview → Confirm → Execute.",
    ]
    if session.has_selection:
        backup = f" from {session.backup_name}" if session.backup_name else ""
        lines.append(f"Selected users: {session.selected_count}{backup}")
    else:
        lines.append("Selected users: none")
    return lines


def _write_operation_placeholder(engine: GroupEngineApplicationService, operation_id: str) -> None:
    info = engine.operation(operation_id)
    if info.available:
        # Future: enter configure → preview → confirm → execute via the engine.
        theme.notify_info(f"{info.label} is available but not wired in this screen yet.")
        theme.pause()
        return
    description = [info.description] if info.description else [f"{info.label} is not ready yet."]
    description.append("Will use the shared Group Engine workflow when implemented.")
    placeholder.coming_soon(Icon.GROUPS, info.label, description)


def _select_users_flow(
    engine: GroupEngineApplicationService,
    checker: GroupCheckerApplicationService,
    workspace: Workspace,
) -> None:
    session = engine.require_session()
    actions = [("1", "Select from backup"), ("2", "Clear selection"), ("0", "Back")]
    theme.page(
        "Select Users",
        theme.body_text(
            [
                "Selection persists until you leave Group Engine.",
                f"Currently selected: {session.selected_count}",
            ]
        ),
        "",
        theme.option_menu(actions),
        icon=Icon.GROUPS,
    )
    choice = Prompt.ask(
        "\nSelect an option",
        choices=[item[0] for item in actions],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return
    if choice == "2":
        engine.clear_selected_users()
        theme.notify_success("Selection cleared.")
        theme.pause()
        return

    backup = _select_backup(checker, workspace)
    if backup is None:
        return

    theme.page(
        "Select Users",
        theme.body_text(
            [
                f"Backup: {backup.name}",
                f"Users in backup: {backup.users}",
                "1. Select all users",
                "2. Enter usernames",
                "0. Back",
            ]
        ),
        icon=Icon.GROUPS,
    )
    mode = Prompt.ask("\nSelect an option", choices=["1", "2", "0"], default="0", show_choices=False)
    if mode == "0":
        return
    try:
        if mode == "1":
            session = engine.select_all_users_from_backup(workspace, backup.name)
        else:
            console.print()
            console.print("[muted]Enter usernames separated by commas or spaces.[/muted]")
            raw = Prompt.ask("\nUsernames", default="").strip()
            names = [part for part in raw.replace(",", " ").split() if part]
            session = engine.select_users_by_username(workspace, backup.name, names)
    except GroupEngineError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return

    theme.notify_success(f"Selected {session.selected_count} user(s).")
    theme.pause()


def _run_check_flow(service: GroupCheckerApplicationService, workspace: Workspace) -> None:
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
            "Check — Failed",
            theme.error_panel("Group Engine could not complete the check", str(exc)),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return
    except Exception as exc:  # noqa: BLE001 — show friendly message, log is in the service
        theme.page(
            "Check — Failed",
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
        theme.page("Check Result", summary, "", table, icon=Icon.GROUPS)
    else:
        theme.page(
            "Check Result",
            summary,
            "",
            theme.body_text(["No users matched this query."]),
            icon=Icon.GROUPS,
        )
    theme.pause()
