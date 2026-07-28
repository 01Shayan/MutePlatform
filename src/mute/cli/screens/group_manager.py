"""Group Manager — Select Target Users → Matched Users → Review → Execute → Report.

Bulk Operations architecture v1.4. Shared Group Selector for every Group pick.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt

from ...core.workspace import Workspace
from ...services.bulk_operations.group_manager import (
    ExecutionReport,
    GroupManagerApplicationService,
    GroupManagerError,
    format_duration_seconds,
    format_home_status,
    format_query_preview,
    format_review_screen,
)
from ...services.bulk_operations.group_manager.target_rules import (
    TargetRule,
    TargetRuleKind,
    compile_target_rules,
    format_rule_checkmarks,
    replace_or_append,
)
from ...ui.components.group_selector import (
    SUBTITLE_CURRENT_GROUPS,
    SUBTITLE_REPLACEMENT_GROUPS,
    SUBTITLE_SELECT_GROUPS,
    SUBTITLE_SELECT_TO_ADD,
    SUBTITLE_SELECT_TO_REMOVE,
    select_groups,
)
from ...ui.copy import (
    BTN_BACK,
    BTN_CONFIRM,
    MATCHED_TITLE,
    MENU_REFRESH_SNAPSHOT,
    MENU_SELECT_TARGET,
    MENU_VIEW_MATCHED,
    MSG_CANCELLED,
    MSG_NO_USERS_MATCHED,
    REPORT_DURATION,
    REPORT_FAILED,
    REPORT_MATCHED,
    REPORT_SUCCESS,
    REPORT_SUMMARY_TITLE,
    REVIEW_TITLE,
    STATUS_COMPLETED,
    STATUS_EXECUTING,
    STATUS_FILTER_CLEARED,
    STATUS_GROUPS_LOADED,
    STATUS_LOADING_SNAPSHOT,
    STATUS_MATCHED_RESET,
    STATUS_NO_CANCEL,
    STATUS_REFRESH_OK,
    STATUS_REFRESHING,
    STATUS_USERS_LOADED,
    TARGET_ADD_RULE,
    TARGET_ALL_USERS,
    TARGET_CONTINUE,
    TARGET_REQUIRE_ALL,
    TARGET_REQUIRE_ANY,
    TARGET_TITLE,
    TARGET_WITH_GROUPS,
    TARGET_WITHOUT_GROUPS,
    TITLE_GROUP_MANAGER,
)
from .. import theme
from ..theme import console


def run(workspace: Workspace) -> None:
    service = GroupManagerApplicationService()
    theme.page(TITLE_GROUP_MANAGER, theme.body_text([STATUS_LOADING_SNAPSHOT]))
    try:
        with console.status(f"[muted]{STATUS_LOADING_SNAPSHOT}[/muted]", spinner="dots"):
            session = service.begin_session(workspace)
    except GroupManagerError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return

    try:
        while True:
            working_set = service.working_set()
            catalog = session.catalog
            matched = working_set.matched if working_set is not None else None
            home = format_home_status(
                workspace=workspace.name,
                snapshot_users=session.snapshot.user_count if session.snapshot else 0,
                available_groups=len(catalog) if catalog else 0,
                working_set_matched=matched,
            )
            choices = [("1", MENU_SELECT_TARGET)]
            if working_set is not None:
                choices.append(("2", MENU_VIEW_MATCHED))
            choices.append(("3", MENU_REFRESH_SNAPSHOT))
            choices.append(("0", BTN_BACK))

            theme.page(
                TITLE_GROUP_MANAGER,
                theme.body_text(home),
                "",
                theme.option_menu(choices),
            )
            choice = Prompt.ask(
                "\nSelect an option",
                choices=[item[0] for item in choices],
                default="0",
                show_choices=False,
            )
            if choice == "0":
                return
            if choice == "1":
                _select_target_flow(service)
            elif choice == "2" and working_set is not None:
                _matched_users_flow(service, workspace)
            elif choice == "3":
                session = _refresh_flow(service, workspace)
    finally:
        service.leave_session()


def _refresh_flow(service: GroupManagerApplicationService, workspace: Workspace):
    theme.page(MENU_REFRESH_SNAPSHOT, theme.body_text([STATUS_REFRESHING]))
    try:
        with console.status(f"[muted]{STATUS_REFRESHING}[/muted]", spinner="dots"):
            session = service.refresh_snapshot(workspace)
    except GroupManagerError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return service.require_session()

    theme.page(
        MENU_REFRESH_SNAPSHOT,
        theme.body_text(
            [
                STATUS_REFRESHING,
                STATUS_USERS_LOADED,
                STATUS_GROUPS_LOADED,
                STATUS_REFRESH_OK,
                STATUS_FILTER_CLEARED,
                STATUS_MATCHED_RESET,
            ]
        ),
    )
    theme.pause()
    return session


def _select_target_flow(service: GroupManagerApplicationService) -> None:
    rules: list[TargetRule] = []
    while True:
        rule = _pick_rule(service, rules)
        if rule is None:
            return
        rules = list(replace_or_append(rules, rule))
        theme.page(
            TARGET_TITLE,
            theme.body_text(format_rule_checkmarks(rules)),
            "",
            theme.option_menu(
                [
                    ("1", TARGET_ADD_RULE),
                    ("2", TARGET_CONTINUE),
                    ("0", BTN_BACK),
                ]
            ),
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=["1", "2", "0"],
            default="2",
            show_choices=False,
        )
        if choice == "0":
            return
        if choice == "1":
            continue
        query = compile_target_rules(rules)
        working_set = service.run_query(query)
        service.require_session().target_rules = tuple(rules)
        if working_set.matched == 0:
            theme.notify_warning(MSG_NO_USERS_MATCHED)
        theme.page(
            MATCHED_TITLE,
            theme.body_text(format_query_preview(working_set, rules=rules)),
        )
        theme.pause()
        return


def _pick_rule(
    service: GroupManagerApplicationService, existing: list[TargetRule]
) -> TargetRule | None:
    options = [
        ("1", TARGET_ALL_USERS),
        ("2", TARGET_WITH_GROUPS),
        ("3", TARGET_WITHOUT_GROUPS),
        ("0", BTN_BACK),
    ]
    body = format_rule_checkmarks(existing) if existing else []
    theme.page(
        TARGET_TITLE,
        theme.body_text(body) if body else theme.body_text(["Who do you want to target?"]),
        "",
        theme.option_menu(options),
    )
    choice = Prompt.ask(
        "\nSelect an option",
        choices=[item[0] for item in options],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return None
    if choice == "1":
        return TargetRule(kind=TargetRuleKind.ALL_USERS)
    if choice == "2":
        return _rule_with_groups(service)
    if choice == "3":
        return _rule_without_groups(service)
    return None


def _rule_with_groups(service: GroupManagerApplicationService) -> TargetRule | None:
    group_ids = _select_target_groups(service)
    if group_ids is None:
        return None
    theme.page(
        TARGET_TITLE,
        theme.body_text(["Selected users should have:"]),
        "",
        theme.option_menu(
            [
                ("1", TARGET_REQUIRE_ALL),
                ("2", TARGET_REQUIRE_ANY),
                ("0", BTN_BACK),
            ]
        ),
    )
    choice = Prompt.ask("\nSelect an option", choices=["1", "2", "0"], default="1", show_choices=False)
    if choice == "0":
        return None
    return TargetRule(
        kind=TargetRuleKind.WITH_GROUPS,
        group_ids=group_ids,
        require_all=(choice == "1"),
    )


def _rule_without_groups(service: GroupManagerApplicationService) -> TargetRule | None:
    group_ids = _select_target_groups(service)
    if group_ids is None:
        return None
    return TargetRule(kind=TargetRuleKind.WITHOUT_GROUPS, group_ids=group_ids)


def _select_target_groups(service: GroupManagerApplicationService) -> tuple[int, ...] | None:
    catalog = service.catalog()
    return select_groups(
        title=TARGET_TITLE,
        subtitle=SUBTITLE_SELECT_GROUPS,
        available_groups=catalog.groups,
    )


def _matched_users_flow(service: GroupManagerApplicationService, workspace: Workspace) -> None:
    working_set = service.require_working_set()
    rules = service.require_session().target_rules
    action_items = [
        (str(index), info.label) for index, info in enumerate(service.list_actions(), start=1)
    ]
    action_items.append(("0", BTN_BACK))
    theme.page(
        MATCHED_TITLE,
        theme.body_text(format_query_preview(working_set, rules=rules)),
        "",
        theme.option_menu(action_items),
    )
    choice = Prompt.ask(
        "\nSelect an action",
        choices=[item[0] for item in action_items],
        default="0",
        show_choices=False,
    )
    if choice == "0":
        return
    info = service.list_actions()[int(choice) - 1]
    _run_action(service, workspace, info.id, info.label)


def _action_subtitle(action_id: str) -> str:
    if action_id == "add":
        return SUBTITLE_SELECT_TO_ADD
    if action_id == "remove":
        return SUBTITLE_SELECT_TO_REMOVE
    if action_id == "replace":
        return SUBTITLE_REPLACEMENT_GROUPS
    return SUBTITLE_SELECT_GROUPS


def _matched_group_union(service: GroupManagerApplicationService) -> list[int]:
    working_set = service.require_working_set()
    catalog_ids = {group.id for group in service.catalog().groups}
    return sorted(
        {
            group_id
            for user in working_set.users
            for group_id in user.group_ids
            if group_id in catalog_ids
        }
    )


def _run_action(
    service: GroupManagerApplicationService,
    workspace: Workspace,
    action_id: str,
    label: str,
) -> None:
    catalog = service.catalog()

    if action_id == "replace":
        current = select_groups(
            title=label,
            subtitle=SUBTITLE_CURRENT_GROUPS,
            available_groups=catalog.groups,
            selected=_matched_group_union(service),
            allow_empty=True,
        )
        if current is None:
            return
        group_ids = select_groups(
            title=label,
            subtitle=SUBTITLE_REPLACEMENT_GROUPS,
            available_groups=catalog.groups,
        )
    else:
        group_ids = select_groups(
            title=label,
            subtitle=_action_subtitle(action_id),
            available_groups=catalog.groups,
        )

    if group_ids is None:
        return

    try:
        service.preview_action(action_id, {"group_ids": group_ids})
    except GroupManagerError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return

    working_set = service.require_working_set()
    rules = service.require_session().target_rules
    theme.page(
        REVIEW_TITLE,
        theme.body_text(
            format_review_screen(
                working_set, action_label=label, group_ids=group_ids, rules=rules
            )
        ),
    )
    if not Confirm.ask(f"\n{BTN_CONFIRM}", default=False):
        theme.notify_info(MSG_CANCELLED)
        theme.pause()
        return

    theme.clear()
    console.print(theme.page_header(STATUS_EXECUTING))
    console.print(theme.body_text([STATUS_NO_CANCEL]))
    try:
        with console.status(f"[muted]{STATUS_EXECUTING}[/muted]", spinner="dots"):
            report = service.execute_action(workspace, action_id, {"group_ids": group_ids})
    except GroupManagerError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return

    _show_report(report)


def _show_report(report: ExecutionReport) -> None:
    theme.page(
        STATUS_COMPLETED,
        theme.summary_panel(
            REPORT_SUMMARY_TITLE,
            [
                (REPORT_MATCHED, str(report.summary.matched)),
                (REPORT_SUCCESS, str(report.summary.success)),
                (REPORT_FAILED, str(report.summary.failed)),
                (REPORT_DURATION, format_duration_seconds(report.duration_ms)),
            ],
            style="success",
        ),
    )
    theme.pause()
