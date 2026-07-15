"""Read-only Telegram navigation handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ....services.workspace import WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..keyboards import back_keyboard, dashboard_keyboard, home_keyboard, workspaces_keyboard
from ..messages import about, coming_next_phase, dashboard, home, settings, workspaces
from ..router import Router


def make_callback_handler(
    authorization: OwnerAuthorization,
    router: Router,
    workspaces_service: WorkspaceApplicationService,
):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update) or update.callback_query is None:
            return
        query = update.callback_query
        chat = update.effective_chat
        if chat is None:
            return
        data = query.data or ""
        if data == "nav:workspaces":
            await query.answer()
            router.workspaces(chat.id)
            items = workspaces_service.navigation_items()
            await query.edit_message_text(workspaces(items), reply_markup=workspaces_keyboard([item.name for item in items]))
        elif data == "nav:settings":
            await query.answer()
            router.settings(chat.id)
            await query.edit_message_text(settings(), reply_markup=back_keyboard())
        elif data == "nav:about":
            await query.answer()
            router.about(chat.id)
            await query.edit_message_text(about(), reply_markup=back_keyboard())
        elif data.startswith("workspace:"):
            await query.answer()
            item = workspaces_service.navigation_item(data.removeprefix("workspace:"))
            if item is None:
                return
            router.dashboard(chat.id, item.name)
            await query.edit_message_text(dashboard(item), reply_markup=dashboard_keyboard())
        elif data == "nav:back":
            await query.answer()
            session = router.back(chat.id)
            if session.current_screen.value == "workspaces":
                items = workspaces_service.navigation_items()
                await query.edit_message_text(workspaces(items), reply_markup=workspaces_keyboard([item.name for item in items]))
            else:
                await query.edit_message_text(home(), reply_markup=home_keyboard())
        elif data.startswith("future:"):
            await query.answer(coming_next_phase(), show_alert=True)

    return handle
