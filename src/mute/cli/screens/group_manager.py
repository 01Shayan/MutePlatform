"""Group Manager — Check Group IDs → Working Set → Actions.

Users are never manually selected. Actions become available only after Check.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.workspace import Workspace
from ...services.backup import format_duration
from ...services.bulk_operations.group_manager import (
    GroupManagerApplicationService,
    GroupManagerError,
    WorkingSet,
)
from ...services.bulk_operations.group_manager.checker import (
    format_group_ids,
    parse_group_ids,
)
from ...services.group_checker.models import GroupQueryDescriptor, GroupQueryType
from .. import theme
from ..theme import Icon, console
from . import placeholder


def run(workspace: Workspace) -> None:
    service = GroupManagerApplicationService()
    service.begin_session(workspace)
    try:
        while True:
            working_set = service.working_set()
            body = [
                "Manage Required Group IDs for users in this workspace.",
                "Check builds a Working Set. Actions operate on that set only.",
            ]
            if working_set is not None:
                body.append(
                    f"Working Set: {working_set.matched_count} matched · "
                    f"{working_set.unmatched_count} unmatched · backup {working_set.backup_name}"
                )
            else:
                body.append("Working Set: none — run Check Group IDs first.")

            actions = [("1", "Check Group IDs")]
            if working_set is not None:
                actions.append(("2", "View Working Set / Actions"))
            actions.append(("0", "Back"))

            theme.page(
                "Group Manager",
                theme.body_text(body),
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
            if choice == "1":
                _run_check_flow(service, workspace)
            elif choice == "2" and working_set is not None:
                _show_working_set_and_actions(service, working_set)
    finally:
        service.leave_session()


def _run_check_flow(service: GroupManagerApplicationService, workspace: Workspace) -> None:
    backup = _select_backup(service, workspace)
    if backup is None:
        return

    theme.page(
        "Check Group IDs",
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
        "Check Confirmation",
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
        theme.notify_info("Cancelled. No check was run.")
        theme.pause()
        return

    theme.clear()
    console.print(theme.page_header("Running Check", Icon.GROUPS))
    console.print()
    try:
        with console.status("[muted]Loading backup and running check…[/muted]", spinner="dots"):
            working_set = service.run_check(
                workspace,
                backup.name,
                GroupQueryDescriptor(GroupQueryType.REQUIRED_GROUPS, group_ids),
            )
    except GroupManagerError as exc:
        theme.page(
            "Check — Failed",
            theme.error_panel("Group Manager could not complete the check", str(exc)),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return
    except Exception as exc:  # noqa: BLE001
        theme.page(
            "Check — Failed",
            theme.error_panel("An unexpected error occurred.", str(exc)),
            icon=Icon.GROUPS,
        )
        theme.pause()
        return

    _show_working_set_and_actions(service, working_set)


def _show_working_set_and_actions(
    service: GroupManagerApplicationService, working_set: WorkingSet
) -> None:
    summary = theme.summary_panel(
        f"{Icon.SUCCESS} Check completed",
        [
            ("Backup", working_set.backup_name),
            ("Query", working_set.query_label),
            ("Required Groups", format_group_ids(working_set.required_group_ids)),
            ("Total Users", str(working_set.total_users)),
            ("Matched Users", str(working_set.matched_count)),
            ("Unmatched Users", str(working_set.unmatched_count)),
            ("Duration", format_duration(working_set.duration_seconds)),
        ],
        style="success",
    )

    body: list = [summary, ""]
    if working_set.matched_users:
        table = theme.data_table(["Username", "Current Groups", "Missing Groups"])
        for row in working_set.matched_users:
            table.add_row(
                row.username,
                format_group_ids(row.current_group_ids),
                format_group_ids(row.missing_group_ids),
            )
        body.extend([theme.body_text(["Matched users (Working Set for Actions):"]), "", table])
    else:
        body.append(theme.body_text(["No users matched this check."]))

    action_items = [
        (str(index), info.label)
        for index, info in enumerate(service.list_actions(), start=1)
    ]
    action_items.append(("0", "Back"))
    body.extend(["", theme.divider(), theme.body_text(["Available Actions"]), "", theme.option_menu(action_items)])

    theme.page("Working Set", *body, icon=Icon.GROUPS)
    choice = Prompt.ask(
        "\nSelect an action",
        choices=[item[0] for item in action_items],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return
    info = service.list_actions()[int(choice) - 1]
    description = [info.description] if info.description else [f"{info.label} is not ready yet."]
    description.append("Operates on the current Working Set — no additional search.")
    placeholder.coming_soon(Icon.GROUPS, info.label, description)


def _select_backup(service: GroupManagerApplicationService, workspace: Workspace):
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
    console.print(
        "[muted]Enter one or more group IDs, separated by commas or spaces (e.g. 1, 3).[/muted]"
    )
    raw = Prompt.ask("\nGroup IDs", default="").strip()
    try:
        return parse_group_ids(raw)
    except ValueError as exc:
        theme.notify_warning(str(exc))
        theme.pause()
        return None
