import json

import pytest

from mute.core.workspace import (
    InvalidWorkspaceName,
    Workspace,
    WorkspaceStore,
    validate_workspace_name,
)


def _store(tmp_path):
    return WorkspaceStore(
        root=tmp_path / "workspaces", registry_path=tmp_path / "config" / "workspaces.json"
    )


def _ws(name):
    return Workspace(name=name, integration="pasarguard", base_url="https://x")


# -- Task 2: unsafe workspace names ---------------------------------------------------


@pytest.mark.parametrize("bad", [".", "..", "", "   ", "a/b", "a\\b", "...", "  .  "])
def test_validate_rejects_unsafe_names(bad):
    with pytest.raises(InvalidWorkspaceName):
        validate_workspace_name(bad)


@pytest.mark.parametrize("bad", ['a:b', "a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"])
def test_validate_rejects_illegal_filesystem_chars(bad):
    with pytest.raises(InvalidWorkspaceName):
        validate_workspace_name(bad)


@pytest.mark.parametrize("bad", ["CON", "nul", "COM1", "lpt9", "aux"])
def test_validate_rejects_reserved_device_names(bad):
    with pytest.raises(InvalidWorkspaceName):
        validate_workspace_name(bad)


def test_validate_trims_and_accepts_normal_names():
    assert validate_workspace_name("  Production  ") == "Production"
    assert validate_workspace_name("My VPN 2") == "My VPN 2"


def test_control_characters_rejected():
    with pytest.raises(InvalidWorkspaceName):
        validate_workspace_name("bad\nname")


def test_store_create_rejects_traversal_name(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(InvalidWorkspaceName):
        store.create(_ws(".."))
    # Nothing outside the workspaces root was created or touched.
    assert store.is_empty()


def test_store_create_strips_and_persists_clean_name(tmp_path):
    store = _store(tmp_path)
    ws = store.create(_ws("  Prod  "), make_active=True)
    assert ws.name == "Prod"
    assert store.exists("Prod")


# -- Task 2: directory collisions -----------------------------------------------------


def test_case_insensitive_directory_collision_is_blocked(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Prod"), make_active=True)
    assert store.dir_is_free("prod") is False
    with pytest.raises(InvalidWorkspaceName):
        store.create(_ws("prod"))


def test_distinct_names_never_share_a_directory(tmp_path):
    store = _store(tmp_path)
    a = store.create(_ws("Alpha"))
    b = store.create(_ws("Beta"))
    assert a.dir != b.dir


# -- Task 3: registry recovery --------------------------------------------------------


def test_recover_from_corrupt_registry(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Prod"), make_active=True)
    store.create(_ws("Staging"))

    # Corrupt the registry file.
    store.registry_path.write_text("{ this is not valid json", encoding="utf-8")

    recovered = _store(tmp_path)
    assert set(recovered.names()) == {"Prod", "Staging"}
    assert recovered.active_name in {"Prod", "Staging"}
    # The registry file was rewritten as valid JSON.
    assert json.loads(recovered.registry_path.read_text(encoding="utf-8"))["workspaces"]


def test_recover_from_missing_registry_with_existing_dirs(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Prod"), make_active=True)

    store.registry_path.unlink()

    recovered = _store(tmp_path)
    assert recovered.names() == ["Prod"]
    assert recovered.active_name == "Prod"


def test_no_recovery_when_nothing_on_disk(tmp_path):
    store = _store(tmp_path)
    assert store.is_empty()
    assert store.active_name is None


def test_corrupt_manifest_is_skipped_during_recovery(tmp_path):
    store = _store(tmp_path)
    good = store.create(_ws("Good"), make_active=True)
    bad = store.create(_ws("Bad"))
    bad.manifest_path.write_text("not json", encoding="utf-8")

    store.registry_path.write_text("broken", encoding="utf-8")
    recovered = _store(tmp_path)
    assert recovered.names() == ["Good"]
    assert good.name == "Good"


# -- Task 5: rename consistency -------------------------------------------------------


def test_rename_updates_manifest_to_match_registry(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Old"), make_active=True)

    assert store.rename("Old", "New") is True

    # Registry reflects the new name.
    assert store.exists("New") and not store.exists("Old")
    assert store.active_name == "New"

    # Manifest on disk matches the registry (no stale workspace_name).
    manifest = json.loads((store.root / "New" / "workspace.json").read_text(encoding="utf-8"))
    assert manifest["workspace_name"] == "New"

    # A fresh load returns a workspace whose name matches the new name.
    reloaded = _store(tmp_path).get("New")
    assert reloaded is not None and reloaded.name == "New"


def test_rename_rejects_unsafe_new_name(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Old"), make_active=True)
    with pytest.raises(InvalidWorkspaceName):
        store.rename("Old", "..")


def test_rename_rejects_collision(tmp_path):
    store = _store(tmp_path)
    store.create(_ws("Alpha"), make_active=True)
    store.create(_ws("Beta"))
    assert store.rename("Alpha", "beta") is False
    assert store.exists("Alpha")
