from mute.core.context import AppContext
from mute.core.integrations import (
    get_integration,
    integration_name,
    list_integrations,
)
from mute.core.workspace import Workspace


def test_resolve_integration_key():
    from mute.core.integrations import resolve_integration_key

    assert resolve_integration_key("pasarguard") == "pasarguard"
    assert resolve_integration_key("PasarGuard") == "pasarguard"
    assert resolve_integration_key("Marzban") == "marzban"


def test_integrations_registry():
    assert get_integration("pasarguard").available is True
    assert get_integration("pasarguard").name == "PasarGuard"
    assert integration_name("pasarguard") == "PasarGuard"
    assert integration_name("unknown") == "unknown"
    # Future integrations are registered but not yet available.
    keys = {it.key for it in list_integrations()}
    assert {"pasarguard", "marzban", "hiddify", "Marzneshin"} <= keys


def test_context_defaults_and_open(tmp_path):
    ctx = AppContext()
    assert ctx.workspace_name == "—"
    assert ctx.integration == "—"

    ws = Workspace(
        name="Production",
        integration="pasarguard",
        base_url="https://panel",
        username="admin",
        root=tmp_path,
    )
    ctx.open_workspace(ws)

    assert ctx.workspace_name == "Production"
    assert ctx.integration == "PasarGuard"
    assert ctx.user == "admin"
