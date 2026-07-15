import json

from mute.core.workspace import Workspace, WorkspaceStore


def _store(tmp_path):
    return WorkspaceStore(
        root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json"
    )


def test_create_lists_and_owns_folders(tmp_path):
    store = _store(tmp_path)
    assert store.is_empty()

    ws = Workspace(
        name="Production",
        integration="pasarguard",
        base_url="https://panel/",
        username="admin",
        password="pw",
    )
    store.create(ws, make_active=True)

    assert store.exists("Production")
    assert store.active_name == "Production"
    assert [w.name for w in store.list()] == ["Production"]

    # Owns its full folder tree.
    for sub in ("backups", "migrations", "reports", "exports", "logs", "cache", "history"):
        assert (ws.dir / sub).is_dir()

    # base_url is normalized (trailing slash removed) and manifest persisted.
    manifest = json.loads(ws.manifest_path.read_text(encoding="utf-8"))
    assert manifest["base_url"] == "https://panel"
    assert manifest["integration"] == "PasarGuard"


def test_reload_persists_and_set_token(tmp_path):
    store = _store(tmp_path)
    store.create(
        Workspace(name="P", integration="pasarguard", base_url="https://x", username="a", password="b"),
        make_active=True,
    )

    # A fresh store reads the same data from disk.
    reloaded = _store(tmp_path)
    ws = reloaded.get_active()
    assert ws is not None and ws.name == "P"

    ws.save_token("tok123")  # bound to its store → persisted
    again = _store(tmp_path).get("P")
    assert again.token == "tok123"


def test_manifest_format_and_readme(tmp_path):
    store = _store(tmp_path)
    ws = store.create(
        Workspace(name="Production", integration="pasarguard", base_url="https://x"),
        make_active=True,
    )
    manifest = json.loads(ws.manifest_path.read_text(encoding="utf-8"))
    assert manifest["workspace_name"] == "Production"
    assert manifest["created_at"]  # stamped on creation

    readme = (ws.dir / "README.md").read_text(encoding="utf-8")
    assert "Workspace\nProduction" in readme
    assert "PasarGuard" in readme


def test_from_dict_accepts_display_name_integration():
    ws = Workspace.from_dict(
        {"workspace_name": "P", "integration": "PasarGuard", "base_url": "https://x"}
    )
    assert ws.integration == "pasarguard"
    assert ws.to_dict()["integration"] == "PasarGuard"


def test_from_dict_accepts_legacy_name_key():
    ws = Workspace.from_dict({"name": "Legacy", "integration": "pasarguard", "base_url": "https://x"})
    assert ws.name == "Legacy"
    assert ws.to_dict()["workspace_name"] == "Legacy"


def test_rename_moves_folder(tmp_path):
    store = _store(tmp_path)
    store.create(
        Workspace(name="Old", integration="pasarguard", base_url="https://x"),
        make_active=True,
    )
    assert store.rename("Old", "New") is True
    assert store.exists("New") and not store.exists("Old")
    assert store.active_name == "New"
    assert (store.root / "New").is_dir()
    assert not (store.root / "Old").exists()


def test_delete_removes_registry_and_dir(tmp_path):
    store = _store(tmp_path)
    ws = store.create(
        Workspace(name="Gone", integration="pasarguard", base_url="https://x"),
        make_active=True,
    )
    path = ws.dir
    assert store.delete("Gone") is True
    assert not store.exists("Gone")
    assert not path.exists()
    assert store.active_name is None
