"""🚀 First-run Setup Wizard.

Runs once, automatically, when no configuration exists. It collects the Telegram installation
details and writes them to the correct places:

    Step 1  Telegram Bot Token   → .env               (BOT_TOKEN)
    Step 2  Telegram Owner ID    → config/settings.json (telegram.owner_ids)
    Step 3  Enable Telegram?     → config/settings.json (telegram.enabled)

Secrets are never written to JSON. After the wizard finishes, the application starts normally
and the wizard never appears again.
"""

from __future__ import annotations

from rich.prompt import Confirm, Prompt
from rich.text import Text

from ...core.config import save_bot_token, save_telegram_config
from .. import theme
from ..theme import Icon, console


def run() -> None:
    """Drive the three-step wizard and persist the collected configuration."""
    _welcome()
    token = _ask_bot_token()
    owner_ids = _ask_owner_ids()
    enabled = _ask_enable_telegram()

    save_bot_token(token)
    save_telegram_config(enabled=enabled, owner_ids=owner_ids)

    _finish(enabled=enabled, owner_ids=owner_ids, has_token=bool(token))


def _welcome() -> None:
    theme.page(
        "Setup Wizard",
        theme.body_text(
            [
                "Welcome to Mute Platform.",
                "",
                "This one-time setup configures the Telegram interface.",
                "Your bot token is stored only in .env; other settings go to config/settings.json.",
            ]
        ),
        icon=Icon.BRAIN,
    )
    console.print()


def _ask_bot_token() -> str:
    console.print(theme.section("Step 1 · Telegram Bot Token", Icon.API))
    console.print(
        Text("Create a bot with @BotFather and paste its token. Leave blank to skip.", style="muted")
    )
    return Prompt.ask("\nTelegram Bot Token", default="", show_default=False).strip()


def _ask_owner_ids() -> list[int]:
    console.print()
    console.print(theme.section("Step 2 · Telegram Owner ID", Icon.PROFILE))
    console.print(
        Text("Only these numeric Telegram user IDs may use the bot. Comma-separate several.", style="muted")
    )
    while True:
        raw = Prompt.ask("\nTelegram Owner ID", default="", show_default=False).strip()
        if not raw:
            return []
        owner_ids = _parse_owner_ids(raw)
        if owner_ids:
            return owner_ids
        theme.notify_warning("Please enter one or more numeric IDs (e.g. 123456789).")


def _ask_enable_telegram() -> bool:
    console.print()
    console.print(theme.section("Step 3 · Enable Telegram", Icon.SHIELD))
    console.print(Text("You can enable the Telegram interface now or later.", style="muted"))
    return Confirm.ask("\nEnable Telegram?", default=True)


def _finish(*, enabled: bool, owner_ids: list[int], has_token: bool) -> None:
    rows = [
        ("Telegram", "Enabled" if enabled else "Disabled"),
        ("Owner IDs", ", ".join(str(item) for item in owner_ids) if owner_ids else "—"),
        ("Bot Token", "Saved to .env" if has_token else "Not set"),
        ("Settings", "config/settings.json"),
    ]
    theme.page(
        "Setup Complete",
        theme.summary_panel(f"{Icon.SUCCESS} Configuration saved", rows, style="success"),
        icon=Icon.BRAIN,
    )
    theme.pause("Press Enter to start")


def _parse_owner_ids(raw: str) -> list[int]:
    owner_ids: list[int] = []
    for chunk in raw.replace(",", " ").split():
        try:
            owner_ids.append(int(chunk))
        except ValueError:
            return []
    return owner_ids
