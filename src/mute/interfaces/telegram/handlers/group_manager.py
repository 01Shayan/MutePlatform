"""Bulk Operations / Group Manager Telegram interface (v1.4 — shared Group Selector)."""

from __future__ import annotations

import asyncio

from telegram import InputFile, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger, use_workspace
from ....core.workspace import Workspace
from ....services.bulk_operations.group_manager import (
    GroupManagerApplicationService,
    GroupManagerError,
)
from ....services.bulk_operations.group_manager.target_rules import (
    TargetRule,
    TargetRuleKind,
    compile_target_rules,
    format_rule_checkmarks,
    replace_or_append,
)
from ....ui.components.group_selector import (
    SUBTITLE_CURRENT_GROUPS,
    SUBTITLE_REPLACEMENT_GROUPS,
    SUBTITLE_SELECT_TO_ADD,
    SUBTITLE_SELECT_TO_REMOVE,
    SUBTITLE_SELECT_GROUPS,
)
from ....ui.copy import STATUS_LOADING_SNAPSHOT as STATUS_LOADING
from ....ui.copy import STATUS_REFRESHING
from ....services.workspace import WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..conversation import begin_temporary, cleanup_temporary
from ..keyboards import (
    bulk_ops_keyboard,
    dashboard_keyboard,
    gm_action_confirm_keyboard,
    gm_action_groups_keyboard,
    gm_actions_keyboard,
    gm_menu_keyboard,
    gm_report_keyboard,
    gm_result_back_keyboard,
    gm_target_groups_keyboard,
    gm_target_menu_keyboard,
    gm_target_require_keyboard,
    gm_target_rules_keyboard,
)
from ..messages import (
    bulk_ops_menu,
    dashboard,
    gm_error,
    gm_group_selector,
    gm_menu,
    gm_need_groups,
    gm_operation_completed,
    gm_refresh_result,
    gm_review,
    gm_running,
    gm_target_groups,
    gm_target_menu,
    gm_target_require,
    gm_target_rules_summary,
    gm_working_set,
)
from ..router import Router

logger = get_logger("telegram")


def make_bulk_ops_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
    group_manager: GroupManagerApplicationService | None = None,
):
    group_manager = group_manager or GroupManagerApplicationService()

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.callback_query is None:
            return
        query = update.callback_query
        chat = update.effective_chat
        if chat is None:
            return

        workspace = _resolve_workspace(router, workspaces_service, chat.id)
        if workspace is None:
            await query.answer("Workspace is no longer available.", show_alert=True)
            return

        session_key = str(chat.id)
        data = query.data or ""
        tg = router.session(chat.id)

        if data == "bulk:menu":
            await query.answer()
            router.bulk_ops(chat.id)
            await _safe_edit(query, bulk_ops_menu(workspace.name), bulk_ops_keyboard())
        elif data == "bulk:dashboard":
            await query.answer()
            group_manager.leave_session(session_key=session_key)
            router.dashboard(chat.id, workspace.name)
            item = workspaces_service.navigation_item(workspace.name)
            await _safe_edit(query, dashboard(item), dashboard_keyboard())
        elif data == "bulk:group_manager":
            await query.answer()
            await _safe_edit(query, STATUS_LOADING)
            try:
                session = await asyncio.to_thread(
                    lambda: group_manager.ensure_session(workspace, session_key=session_key)
                )
            except GroupManagerError as exc:
                await _safe_edit(query, gm_error(str(exc)), bulk_ops_keyboard())
                return
            router.group_manager(chat.id)
            await _safe_edit(
                query,
                gm_menu(workspace.name, session=session),
                gm_menu_keyboard(has_working_set=session.has_working_set),
            )
        elif data == "gm:query":
            await query.answer()
            tg.draft = {"rules": [], "selected": [], "pending_kind": None}
            router.gm_target_menu(chat.id)
            await _safe_edit(query, gm_target_menu(), gm_target_menu_keyboard())
        elif data == "gm:target_menu":
            await query.answer()
            rules = _draft_rules(tg.draft)
            router.gm_target_menu(chat.id)
            await _safe_edit(
                query,
                gm_target_menu(rules_text=format_rule_checkmarks(rules) if rules else None),
                gm_target_menu_keyboard(),
            )
        elif data == "gm:target:all":
            await query.answer()
            rules = replace_or_append(_draft_rules(tg.draft), TargetRule(kind=TargetRuleKind.ALL_USERS))
            tg.draft["rules"] = _serialize_rules(rules)
            router.gm_target_rules(chat.id)
            await _safe_edit(
                query,
                gm_target_rules_summary(format_rule_checkmarks(rules)),
                gm_target_rules_keyboard(),
            )
        elif data == "gm:target:with":
            await query.answer()
            tg.draft["pending_kind"] = TargetRuleKind.WITH_GROUPS.value
            tg.draft["selected"] = []
            catalog = group_manager.catalog(session_key=session_key)
            router.gm_target_groups(chat.id)
            await _safe_edit(
                query,
                gm_target_groups(groups=catalog.groups, selected_ids=[]),
                gm_target_groups_keyboard(catalog.groups, set()),
            )
        elif data == "gm:target:without":
            await query.answer()
            tg.draft["pending_kind"] = TargetRuleKind.WITHOUT_GROUPS.value
            tg.draft["selected"] = []
            catalog = group_manager.catalog(session_key=session_key)
            router.gm_target_groups(chat.id)
            await _safe_edit(
                query,
                gm_target_groups(groups=catalog.groups, selected_ids=[]),
                gm_target_groups_keyboard(catalog.groups, set()),
            )
        elif data.startswith("gm:toggle:"):
            await query.answer()
            group_id = int(data.removeprefix("gm:toggle:"))
            selected = set(tg.draft.get("selected") or [])
            if group_id in selected:
                selected.remove(group_id)
            else:
                selected.add(group_id)
            tg.draft["selected"] = sorted(selected)
            catalog = group_manager.catalog(session_key=session_key)
            await _safe_edit(
                query,
                gm_target_groups(groups=catalog.groups, selected_ids=tg.draft["selected"]),
                gm_target_groups_keyboard(catalog.groups, selected),
            )
        elif data == "gm:groups_done":
            selected = list(tg.draft.get("selected") or [])
            if not selected:
                await query.answer(gm_need_groups(), show_alert=True)
                return
            await query.answer()
            kind = tg.draft.get("pending_kind")
            if kind == TargetRuleKind.WITH_GROUPS.value:
                router.gm_target_require(chat.id)
                await _safe_edit(query, gm_target_require(), gm_target_require_keyboard())
            else:
                rule = TargetRule(
                    kind=TargetRuleKind.WITHOUT_GROUPS,
                    group_ids=tuple(selected),
                )
                rules = replace_or_append(_draft_rules(tg.draft), rule)
                tg.draft["rules"] = _serialize_rules(rules)
                tg.draft["pending_kind"] = None
                router.gm_target_rules(chat.id)
                await _safe_edit(
                    query,
                    gm_target_rules_summary(format_rule_checkmarks(rules)),
                    gm_target_rules_keyboard(),
                )
        elif data.startswith("gm:require:"):
            await query.answer()
            require_all = data.endswith(":all")
            selected = tuple(tg.draft.get("selected") or [])
            rule = TargetRule(
                kind=TargetRuleKind.WITH_GROUPS,
                group_ids=selected,
                require_all=require_all,
            )
            rules = replace_or_append(_draft_rules(tg.draft), rule)
            tg.draft["rules"] = _serialize_rules(rules)
            tg.draft["pending_kind"] = None
            router.gm_target_rules(chat.id)
            await _safe_edit(
                query,
                gm_target_rules_summary(format_rule_checkmarks(rules)),
                gm_target_rules_keyboard(),
            )
        elif data == "gm:add_rule":
            await query.answer()
            rules = _draft_rules(tg.draft)
            router.gm_target_menu(chat.id)
            await _safe_edit(
                query,
                gm_target_menu(rules_text=format_rule_checkmarks(rules)),
                gm_target_menu_keyboard(),
            )
        elif data == "gm:apply_rules":
            await query.answer()
            rules = _draft_rules(tg.draft)
            if not rules:
                await query.answer("Add at least one rule.", show_alert=True)
                return
            query_obj = compile_target_rules(rules)
            working_set = group_manager.run_query(query_obj, session_key=session_key)
            group_manager.require_session(session_key=session_key).target_rules = tuple(rules)
            router.gm_working_set(chat.id)
            await _safe_edit(
                query,
                gm_working_set(working_set, rules=rules),
                gm_actions_keyboard(group_manager.list_actions()),
            )
        elif data == "gm:working_set":
            await query.answer()
            working_set = group_manager.working_set(session_key=session_key)
            if working_set is None:
                await query.answer("Select target users first.", show_alert=True)
                return
            rules = group_manager.require_session(session_key=session_key).target_rules
            router.gm_working_set(chat.id)
            await _safe_edit(
                query,
                gm_working_set(working_set, rules=rules),
                gm_actions_keyboard(group_manager.list_actions()),
            )
        elif data == "gm:refresh":
            await query.answer()
            await _safe_edit(query, STATUS_REFRESHING)
            try:
                session = await asyncio.to_thread(
                    lambda: group_manager.refresh_snapshot(workspace, session_key=session_key)
                )
            except GroupManagerError as exc:
                await _safe_edit(query, gm_error(str(exc)), gm_result_back_keyboard())
                return
            router.group_manager(chat.id)
            await _safe_edit(
                query,
                f"{gm_refresh_result()}\n\n{gm_menu(workspace.name, session=session)}",
                gm_menu_keyboard(has_working_set=session.has_working_set),
            )
        elif data.startswith("gm:action:"):
            await query.answer()
            action_id = data.removeprefix("gm:action:")
            begin_temporary(router, chat.id)
            session = router.gm_action_input(chat.id, action_id)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            info = group_manager.action(action_id)
            catalog = group_manager.catalog(session_key=session_key)
            selected: list[int] = []
            replace_step = None
            subtitle = _action_subtitle(action_id)
            if action_id == "replace":
                replace_step = "current"
                subtitle = SUBTITLE_CURRENT_GROUPS
                selected = _matched_group_union(group_manager, session_key)
            session.draft = {
                **(session.draft or {}),
                "action_id": action_id,
                "selected": selected,
                "replace_step": replace_step,
            }
            await _safe_edit(
                query,
                gm_group_selector(
                    title=info.label,
                    subtitle=subtitle,
                    groups=catalog.groups,
                    selected_ids=selected,
                ),
                gm_action_groups_keyboard(catalog.groups, selected),
            )
        elif data.startswith("gm:asel:"):
            await query.answer()
            group_id = int(data.removeprefix("gm:asel:"))
            selected = set(tg.draft.get("selected") or [])
            if group_id in selected:
                selected.remove(group_id)
            else:
                selected.add(group_id)
            tg.draft["selected"] = sorted(selected)
            action_id = tg.draft.get("action_id") or ""
            info = group_manager.action(action_id)
            catalog = group_manager.catalog(session_key=session_key)
            subtitle = _action_screen_subtitle(action_id, tg.draft.get("replace_step"))
            await _safe_edit(
                query,
                gm_group_selector(
                    title=info.label,
                    subtitle=subtitle,
                    groups=catalog.groups,
                    selected_ids=tg.draft["selected"],
                ),
                gm_action_groups_keyboard(catalog.groups, selected),
            )
        elif data == "gm:action_done":
            selected = list(tg.draft.get("selected") or [])
            action_id = tg.draft.get("action_id") or ""
            replace_step = tg.draft.get("replace_step")
            allow_empty = action_id == "replace" and replace_step == "current"
            if not selected and not allow_empty:
                await query.answer(gm_need_groups(), show_alert=True)
                return
            await query.answer()
            if action_id == "replace" and replace_step == "current":
                tg.draft["replace_step"] = "replacement"
                tg.draft["selected"] = []
                catalog = group_manager.catalog(session_key=session_key)
                info = group_manager.action(action_id)
                await _safe_edit(
                    query,
                    gm_group_selector(
                        title=info.label,
                        subtitle=SUBTITLE_REPLACEMENT_GROUPS,
                        groups=catalog.groups,
                        selected_ids=[],
                    ),
                    gm_action_groups_keyboard(catalog.groups, set()),
                )
                return
            await _show_action_review(
                query, router, group_manager, chat.id, action_id, tuple(selected)
            )
        elif data == "gm:confirm":
            await query.answer()
            await _execute_confirmed(
                update, context, router, group_manager, workspace, chat.id
            )
        elif data.startswith("gm:download:"):
            await query.answer()
            name = data.removeprefix("gm:download:")
            path = workspace.reports_dir / name
            if not path.is_file():
                await query.answer("Report file not found.", show_alert=True)
                return
            await context.bot.send_document(
                chat_id=chat.id,
                document=InputFile(path.open("rb"), filename=path.name),
            )
        elif data == "gm:back_manager":
            await query.answer()
            session = group_manager.require_session(session_key=session_key)
            router.group_manager(chat.id)
            await _safe_edit(
                query,
                gm_menu(workspace.name, session=session),
                gm_menu_keyboard(has_working_set=session.has_working_set),
            )

    return handle


def make_group_manager_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
    group_manager: GroupManagerApplicationService | None = None,
):
    """Legacy text path removed — Group selection uses the shared selector only."""

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        return

    return handle


async def _show_action_review(query, router, group_manager, chat_id, action_id, group_ids):
    session_key = str(chat_id)
    try:
        group_manager.preview_action(
            action_id, {"group_ids": group_ids}, session_key=session_key
        )
    except GroupManagerError as exc:
        await _safe_edit(query, gm_error(str(exc)), gm_result_back_keyboard())
        return
    session = router.session(chat_id)
    session.draft["group_ids"] = list(group_ids)
    session.draft["action_id"] = action_id
    working_set = group_manager.require_working_set(session_key=session_key)
    rules = group_manager.require_session(session_key=session_key).target_rules
    info = group_manager.action(action_id)
    router.gm_action_confirm(chat_id, action_id)
    await _safe_edit(
        query,
        gm_review(working_set, action_label=info.label, group_ids=group_ids, rules=rules),
        gm_action_confirm_keyboard(),
    )


async def _execute_confirmed(update, context, router, group_manager, workspace, chat_id):
    query = update.callback_query
    session = router.session(chat_id)
    action_id = session.draft.get("action_id") or ""
    group_ids = tuple(session.draft.get("group_ids") or ())
    message_id = query.message.message_id if query.message else session.last_message_id
    await _safe_edit_message(context, chat_id, message_id, gm_running())
    try:
        report = await asyncio.to_thread(
            lambda: group_manager.execute_action(
                workspace,
                action_id,
                {"group_ids": group_ids},
                session_key=str(chat_id),
            )
        )
    except GroupManagerError as exc:
        await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
        await _safe_edit_message(
            context, chat_id, message_id, gm_error(str(exc)), gm_result_back_keyboard()
        )
        return
    await cleanup_temporary(context.bot, router, chat_id, keep=message_id)
    router.gm_report(chat_id)
    filename = report.path.name if report.path else ""
    await _safe_edit_message(
        context,
        chat_id,
        message_id,
        gm_operation_completed(report),
        gm_report_keyboard(filename),
    )


def _action_subtitle(action_id: str) -> str:
    if action_id == "add":
        return SUBTITLE_SELECT_TO_ADD
    if action_id == "remove":
        return SUBTITLE_SELECT_TO_REMOVE
    if action_id == "replace":
        return SUBTITLE_REPLACEMENT_GROUPS
    return SUBTITLE_SELECT_GROUPS


def _action_screen_subtitle(action_id: str, replace_step: str | None) -> str:
    if action_id == "replace":
        if replace_step == "current":
            return SUBTITLE_CURRENT_GROUPS
        return SUBTITLE_REPLACEMENT_GROUPS
    return _action_subtitle(action_id)


def _matched_group_union(group_manager: GroupManagerApplicationService, session_key: str) -> list[int]:
    working_set = group_manager.require_working_set(session_key=session_key)
    catalog_ids = {group.id for group in group_manager.catalog(session_key=session_key).groups}
    return sorted(
        {
            group_id
            for user in working_set.users
            for group_id in user.group_ids
            if group_id in catalog_ids
        }
    )


def _draft_rules(draft: dict) -> list[TargetRule]:
    raw = draft.get("rules") or []
    rules: list[TargetRule] = []
    for item in raw:
        kind = TargetRuleKind(item["kind"])
        rules.append(
            TargetRule(
                kind=kind,
                group_ids=tuple(item.get("group_ids") or ()),
                require_all=bool(item.get("require_all", True)),
            )
        )
    return rules


def _serialize_rules(rules) -> list[dict]:
    return [
        {
            "kind": rule.kind.value,
            "group_ids": list(rule.group_ids),
            "require_all": rule.require_all,
        }
        for rule in rules
    ]


def _resolve_workspace(router, workspaces_service, chat_id) -> Workspace | None:
    name = router.session(chat_id).current_workspace
    if not name:
        return None
    workspace = workspaces_service.workspace(name)
    if workspace is not None:
        use_workspace(workspace.logs_dir)
    return workspace


async def _safe_edit(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise


async def _safe_edit_message(context, chat_id, message_id, text, reply_markup=None) -> None:
    if message_id is None:
        return
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
