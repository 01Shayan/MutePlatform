"""python-telegram-bot application construction and polling lifecycle."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from ...core.logging import get_logger
from ...services.workspace import WorkspaceApplicationService
from .auth import OwnerAuthorization
from .handlers.backup import make_backup_handler
from .handlers.navigation import make_callback_handler
from .handlers.start import make_start_handler
from .messages import friendly_error
from .router import Router
from .session import SessionManager

logger = get_logger("telegram")


def build_bot(
    token: str,
    authorization: OwnerAuthorization,
    *,
    workspaces_service: WorkspaceApplicationService | None = None,
) -> Application:
    """Build an owner-only polling application without starting network activity."""
    _ensure_event_loop()
    sessions = SessionManager()
    router = Router(sessions)
    workspaces_service = workspaces_service or WorkspaceApplicationService.for_navigation()
    application = ApplicationBuilder().token(token).build()
    application.bot_data["telegram_authorization"] = authorization
    application.bot_data["telegram_sessions"] = sessions
    application.bot_data["telegram_router"] = router
    application.bot_data["telegram_workspace_service"] = workspaces_service
    application.add_handler(CommandHandler("start", make_start_handler(authorization, router)))
    application.add_handler(
        CallbackQueryHandler(
            make_backup_handler(authorization, router, workspaces_service), pattern=r"^backup:"
        )
    )
    application.add_handler(CallbackQueryHandler(make_callback_handler(authorization, router, workspaces_service)))
    application.add_error_handler(error_handler)
    return application


def _ensure_event_loop() -> None:
    """Support Python versions where a synchronous caller has no current event loop."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def run_polling(application: Application) -> None:
    """Run the bot using polling only."""
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected errors and give authorized users a safe generic reply."""
    logger.exception("Unhandled Telegram update", exc_info=context.error)
    authorization = context.application.bot_data.get("telegram_authorization")
    if not isinstance(authorization, OwnerAuthorization) or not isinstance(update, Update):
        return
    if not authorization.allows_update(update) or update.effective_message is None:
        return
    await update.effective_message.reply_text(friendly_error())
