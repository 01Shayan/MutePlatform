"""Foundation-only /start handler; it intentionally exposes no application features."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..auth import OwnerAuthorization
from ..keyboards import home_keyboard
from ..messages import home
from ..router import Router


def make_start_handler(authorization: OwnerAuthorization, router: Router):
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorization.allows_update(update):
            return
        chat = update.effective_chat
        if chat is None:
            return
        router.home(chat.id)
        await update.effective_message.reply_text(home(), reply_markup=home_keyboard())

    return start
