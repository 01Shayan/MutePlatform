import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

telegram = pytest.importorskip("telegram")

from mute.interfaces.telegram.auth import OwnerAuthorization
from mute.interfaces.telegram.bot import build_bot, run_polling
from mute.interfaces.telegram.handlers.navigation import make_callback_handler
from mute.interfaces.telegram.handlers.start import make_start_handler
from mute.interfaces.telegram.keyboards import inline_keyboard
from mute.interfaces.telegram.router import Router
from mute.interfaces.telegram.session import Screen, SessionManager
from mute.services.workspace import WorkspaceNavigationItem


class FakeWorkspaceService:
    def __init__(self):
        self.items = [WorkspaceNavigationItem("Production", "PasarGuard")]

    def navigation_items(self):
        return self.items

    def navigation_item(self, name):
        return next((item for item in self.items if item.name == name), None)


def test_authorization_accepts_only_configured_owner_ids():
    authorization = OwnerAuthorization(frozenset({10, 20}))

    assert authorization.allows(10)
    assert authorization.allows(20)
    assert not authorization.allows(99)
    assert not authorization.allows(None)


def test_session_manager_keeps_one_navigation_session_per_chat():
    sessions = SessionManager()
    router = Router(sessions)

    first = router.go_to(100, Screen.HOME, action="start")
    second = sessions.get(100)

    assert first is second
    assert second.current_workspace is None
    assert second.current_screen is Screen.HOME
    assert second.current_action == "start"
    assert sessions.get(200) is not second


def test_keyboard_builder_creates_buttons():
    keyboard = inline_keyboard([[('Home', 'home')]])

    assert keyboard.inline_keyboard[0][0].text == "Home"
    assert keyboard.inline_keyboard[0][0].callback_data == "home"


def test_unauthorized_start_is_silently_ignored():
    reply = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=999),
        effective_chat=SimpleNamespace(id=1),
        effective_message=SimpleNamespace(reply_text=reply),
    )
    handler = make_start_handler(OwnerAuthorization(frozenset({1})), Router(SessionManager()))

    asyncio.run(handler(update, None))

    reply.assert_not_awaited()


def test_authorized_start_opens_home():
    sessions = SessionManager()
    reply = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=1),
        effective_message=SimpleNamespace(reply_text=reply),
    )
    handler = make_start_handler(OwnerAuthorization(frozenset({1})), Router(sessions))

    asyncio.run(handler(update, None))

    assert sessions.get(1).current_screen is Screen.HOME
    reply.assert_awaited_once()


def test_bot_builds_and_polling_delegates_without_starting_services(monkeypatch):
    application = build_bot(
        "123456:test-token", OwnerAuthorization(frozenset({1})), workspaces_service=FakeWorkspaceService()
    )
    assert application.bot_data["telegram_sessions"] is not None
    assert application.bot_data["telegram_router"] is not None

    calls = []
    fake_application = SimpleNamespace(run_polling=lambda **kwargs: calls.append(kwargs))
    run_polling(fake_application)

    assert calls == [{"allowed_updates": telegram.Update.ALL_TYPES}]


def test_workspace_navigation_updates_session_and_never_executes_actions():
    sessions = SessionManager()
    router = Router(sessions)
    handler = make_callback_handler(
        OwnerAuthorization(frozenset({1})), router, FakeWorkspaceService()
    )
    query = SimpleNamespace(data="nav:workspaces", answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=10), callback_query=query)

    asyncio.run(handler(update, None))
    assert sessions.get(10).current_screen is Screen.WORKSPACES

    query.data = "workspace:Production"
    asyncio.run(handler(update, None))
    session = sessions.get(10)
    assert session.current_screen is Screen.DASHBOARD
    assert session.current_workspace == "Production"

    query.data = "nav:back"
    asyncio.run(handler(update, None))
    assert sessions.get(10).current_screen is Screen.WORKSPACES
    assert sessions.get(10).current_workspace is None


def test_settings_about_and_future_actions_are_navigation_only():
    sessions = SessionManager()
    router = Router(sessions)
    handler = make_callback_handler(
        OwnerAuthorization(frozenset({1})), router, FakeWorkspaceService()
    )
    query = SimpleNamespace(data="nav:settings", answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=10), callback_query=query)

    asyncio.run(handler(update, None))
    assert sessions.get(10).current_screen is Screen.SETTINGS
    query.data = "nav:about"
    asyncio.run(handler(update, None))
    assert sessions.get(10).current_screen is Screen.ABOUT
    query.data = "future:backup"
    asyncio.run(handler(update, None))
    query.answer.assert_awaited_with("Coming in the next phase.", show_alert=True)
