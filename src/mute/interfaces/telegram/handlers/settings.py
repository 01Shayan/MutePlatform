"""Telegram Settings — reset tokens, bot token, and owner IDs via application services."""

from __future__ import annotations

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ....core.logging import get_logger
from ....services.settings import SettingsApplicationService, SettingsOperationError
from ....services.workspace import WorkspaceApplicationService
from ..auth import OwnerAuthorization
from ..conversation import begin_temporary, cleanup_temporary, track_temporary
from ..keyboards import cancel_keyboard, settings_keyboard, yes_no_keyboard
from ..messages import (
    ask_bot_token,
    ask_owner_ids,
    bot_token_updated,
    change_bot_token_confirmation,
    change_owner_ids_confirmation,
    owner_ids_updated,
    reset_tokens_confirmation,
    reset_tokens_success,
    settings,
    settings_error,
)
from ..router import Router
from ..session import Screen

logger = get_logger("telegram")

_TEXT_SCREENS = {
    Screen.SETTINGS_BOT_TOKEN_INPUT,
    Screen.SETTINGS_OWNER_INPUT,
}


def make_settings_handler(
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

        if data == "settings:reset-tokens":
            await query.answer()
            router.go_to(chat.id, Screen.SETTINGS_RESET_TOKENS_CONFIRM)
            await _safe_edit(
                query,
                reset_tokens_confirmation(),
                yes_no_keyboard("settings:reset-tokens-yes", "settings:reset-tokens-no"),
            )
        elif data == "settings:reset-tokens-yes":
            await query.answer()
            count = workspaces_service.clear_all_tokens()
            router.settings(chat.id)
            await cleanup_temporary(context.bot, router, chat.id)
            await _safe_edit(
                query,
                f"{reset_tokens_success(count)}\n\n{settings()}",
                settings_keyboard(),
            )
        elif data == "settings:reset-tokens-no":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_settings(query, router, chat.id)
        elif data == "settings:bot-token":
            await query.answer()
            router.go_to(chat.id, Screen.SETTINGS_BOT_TOKEN_CONFIRM)
            await _safe_edit(
                query,
                change_bot_token_confirmation(),
                yes_no_keyboard("settings:bot-token-yes", "settings:bot-token-no"),
            )
        elif data == "settings:bot-token-yes":
            await query.answer()
            begin_temporary(router, chat.id)
            router.go_to(chat.id, Screen.SETTINGS_BOT_TOKEN_INPUT)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(query, ask_bot_token(), cancel_keyboard("settings:cancel"))
        elif data == "settings:bot-token-no":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_settings(query, router, chat.id)
        elif data == "settings:owner-ids":
            await query.answer()
            router.go_to(chat.id, Screen.SETTINGS_OWNER_CONFIRM)
            await _safe_edit(
                query,
                change_owner_ids_confirmation(),
                yes_no_keyboard("settings:owner-ids-yes", "settings:owner-ids-no"),
            )
        elif data == "settings:owner-ids-yes":
            await query.answer()
            begin_temporary(router, chat.id)
            router.go_to(chat.id, Screen.SETTINGS_OWNER_INPUT)
            if query.message is not None:
                router.remember_message(chat.id, query.message.message_id)
            await _safe_edit(query, ask_owner_ids(), cancel_keyboard("settings:cancel"))
        elif data == "settings:owner-ids-no":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_settings(query, router, chat.id)
        elif data == "settings:cancel":
            await query.answer()
            await cleanup_temporary(context.bot, router, chat.id)
            await _show_settings(query, router, chat.id)

    return handle


def make_settings_text_handler(
    authorization: OwnerAuthorization,
    router: Router,
    settings_service: SettingsApplicationService | None = None,
):
    settings_service = settings_service or SettingsApplicationService()

    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle settings text input. Returns True when the update was consumed."""
        if not authorization.allows_update(update) or update.effective_message is None:
            return False
        chat = update.effective_chat
        if chat is None:
            return False
        session = router.session(chat.id)
        if session.current_screen not in _TEXT_SCREENS:
            return False

        text = (update.effective_message.text or "").strip()
        track_temporary(router, chat.id, update.effective_message.message_id)
        try:
            if session.current_screen is Screen.SETTINGS_BOT_TOKEN_INPUT:
                settings_service.update_bot_token(text)
                router.settings(chat.id)
                await cleanup_temporary(context.bot, router, chat.id)
                await _edit_or_reply(
                    context,
                    router,
                    chat.id,
                    update,
                    f"{bot_token_updated()}\n\n{settings()}",
                    settings_keyboard(),
                )
            elif session.current_screen is Screen.SETTINGS_OWNER_INPUT:
                owner_ids = settings_service.update_owner_ids(text)
                router.settings(chat.id)
                await cleanup_temporary(context.bot, router, chat.id)
                await _edit_or_reply(
                    context,
                    router,
                    chat.id,
                    update,
                    f"{owner_ids_updated(owner_ids)}\n\n{settings()}",
                    settings_keyboard(),
                )
        except SettingsOperationError as exc:
            sent = await update.effective_message.reply_text(settings_error(str(exc)))
            track_temporary(router, chat.id, sent.message_id)
        except Exception:  # noqa: BLE001 — surface a friendly message, log the detail
            logger.exception("Unexpected error during Telegram settings update")
            sent = await update.effective_message.reply_text(settings_error("Please try again."))
            track_temporary(router, chat.id, sent.message_id)
        return True

    return handle


async def _show_settings(query, router: Router, chat_id: int) -> None:
    router.settings(chat_id)
    await _safe_edit(query, settings(), settings_keyboard())


async def _edit_or_reply(context, router, chat_id, update, text, reply_markup) -> None:
    message_id = router.session(chat_id).last_message_id
    if message_id is not None:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
            )
            return
        except BadRequest:
            track_temporary(router, chat_id, message_id)
    sent = await update.effective_message.reply_text(text, reply_markup=reply_markup)
    router.remember_message(chat_id, sent.message_id)


async def _safe_edit(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            raise
