"""⚙️ Settings — mirrors Telegram Settings via SettingsApplicationService."""

from __future__ import annotations

from rich.prompt import Prompt

from ...services.settings import SettingsApplicationService, SettingsOperationError
from ...services.workspace import WorkspaceApplicationService
from .. import theme
from ..theme import Icon


_ACTIONS = [
    ("1", "Reset Workspace Tokens"),
    ("2", "Change Bot Token"),
    ("3", "Change Owner IDs"),
    ("0", "Back"),
]


def show() -> None:
    while True:
        theme.page(
            "Settings",
            theme.body_text(
                [
                    "Manage Telegram and workspace credentials.",
                    "",
                    "1. Reset Workspace Tokens",
                    "2. Change Bot Token",
                    "3. Change Owner IDs",
                ]
            ),
            "",
            theme.option_menu(_ACTIONS),
            icon=Icon.SETTINGS,
        )
        choice = Prompt.ask(
            "\nSelect an option",
            choices=[key for key, _ in _ACTIONS],
            default="0",
            show_choices=False,
        )
        if choice == "0":
            return
        if choice == "1":
            _reset_workspace_tokens()
        elif choice == "2":
            _change_bot_token()
        elif choice == "3":
            _change_owner_ids()


def _reset_workspace_tokens() -> None:
    theme.page(
        "Reset Workspace Tokens",
        theme.body_text(
            [
                "This will remove all saved workspace tokens.",
                "",
                "Workspace configuration,",
                "passwords,",
                "backups",
                "and history",
                "will remain.",
                "",
                "Continue?",
            ]
        ),
        "",
        theme.option_menu([("1", "Yes"), ("0", "No")]),
        icon=Icon.SETTINGS,
    )
    choice = Prompt.ask(
        "\nSelect an option", choices=["1", "0"], default="0", show_choices=False
    )
    if choice != "1":
        return
    WorkspaceApplicationService.for_navigation().clear_all_tokens()
    theme.notify_success("Workspace tokens removed successfully.")
    theme.pause()


def _change_bot_token() -> None:
    theme.page(
        "Change Bot Token",
        theme.body_text(
            [
                "You will be asked for a new BOT_TOKEN.",
                "Restart the bot after saving to apply the change.",
                "",
                "Continue?",
            ]
        ),
        "",
        theme.option_menu([("1", "Yes"), ("0", "No")]),
        icon=Icon.SETTINGS,
    )
    choice = Prompt.ask(
        "\nSelect an option", choices=["1", "0"], default="0", show_choices=False
    )
    if choice != "1":
        return

    token = Prompt.ask("\nTelegram Bot Token", default="", show_default=False).strip()
    try:
        SettingsApplicationService().update_bot_token(token)
    except SettingsOperationError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return
    theme.notify_success("Bot token updated successfully.")
    theme.notify_info("Restart the bot to apply the changes.")
    theme.pause()


def _change_owner_ids() -> None:
    theme.page(
        "Change Owner IDs",
        theme.body_text(
            [
                "You will be asked for one or more Telegram owner IDs.",
                "Restart the bot after saving to apply the change.",
                "",
                "Continue?",
            ]
        ),
        "",
        theme.option_menu([("1", "Yes"), ("0", "No")]),
        icon=Icon.SETTINGS,
    )
    choice = Prompt.ask(
        "\nSelect an option", choices=["1", "0"], default="0", show_choices=False
    )
    if choice != "1":
        return

    raw = Prompt.ask(
        "\nOwner IDs (e.g. 123456789 or 123456789,987654321)",
        default="",
        show_default=False,
    ).strip()
    try:
        owner_ids = SettingsApplicationService().update_owner_ids(raw)
    except SettingsOperationError as exc:
        theme.notify_error(str(exc))
        theme.pause()
        return
    joined = ", ".join(str(value) for value in owner_ids)
    theme.notify_success("Owner IDs updated successfully.")
    theme.notify_info(f"Owner IDs: {joined}")
    theme.notify_info("Restart the bot to apply the changes.")
    theme.pause()
