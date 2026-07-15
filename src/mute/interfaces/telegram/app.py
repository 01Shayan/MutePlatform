"""Independent entry point for the Telegram polling interface."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.config import telegram_settings
from .auth import OwnerAuthorization
from .bot import build_bot, run_polling


class TelegramConfigurationError(RuntimeError):
    """Raised when the Telegram interface has not been configured yet."""


@dataclass(frozen=True)
class TelegramConfiguration:
    token: str
    enabled: bool
    authorization: OwnerAuthorization


def load_configuration() -> TelegramConfiguration:
    try:
        settings = telegram_settings()
    except ValueError as exc:
        raise TelegramConfigurationError(str(exc)) from exc
    if not settings.enabled:
        raise TelegramConfigurationError("Telegram is disabled in config/settings.json.")
    if not settings.bot_token:
        raise TelegramConfigurationError("BOT_TOKEN is missing from .env.")
    if not settings.owner_ids:
        raise TelegramConfigurationError("At least one Telegram owner ID is required.")
    return TelegramConfiguration(
        settings.bot_token, True, OwnerAuthorization(settings.owner_ids)
    )


def create_application():
    configuration = load_configuration()
    application = build_bot(configuration.token, configuration.authorization)
    application.bot_data["telegram_authorization"] = configuration.authorization
    return application


def run() -> None:
    run_polling(create_application())


if __name__ == "__main__":
    run()
