import json

import pytest

from mute.core.jsonio import unique_path, write_json_atomic


def test_write_creates_file_and_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "deep" / "data.json"
    write_json_atomic(target, {"a": 1, "b": [2, 3]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1, "b": [2, 3]}


def test_write_leaves_no_temp_files_behind(tmp_path):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"ok": True})
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]


def test_failed_serialization_preserves_previous_file(tmp_path):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"version": 1})

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        write_json_atomic(target, {"bad": Unserializable()})

    # Original content is untouched and no stray temp file remains.
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]


def test_replace_is_atomic_overwrite(tmp_path):
    target = tmp_path / "data.json"
    write_json_atomic(target, {"n": 1})
    write_json_atomic(target, {"n": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"n": 2}


def test_mode_is_applied(tmp_path):
    target = tmp_path / "secret.json"
    write_json_atomic(target, {"x": 1}, mode=0o600)
    assert (target.stat().st_mode & 0o777) == 0o600


def test_ensure_ascii_false_keeps_unicode(tmp_path):
    target = tmp_path / "u.json"
    write_json_atomic(target, {"name": "München"}, ensure_ascii=False)
    assert "München" in target.read_text(encoding="utf-8")


def test_unique_path_returns_base_when_free(tmp_path):
    assert unique_path(tmp_path, "backup_2026", ".json") == tmp_path / "backup_2026.json"


def test_unique_path_suffixes_on_collision(tmp_path):
    (tmp_path / "backup_2026.json").write_text("{}", encoding="utf-8")
    first = unique_path(tmp_path, "backup_2026", ".json")
    assert first == tmp_path / "backup_2026_2.json"

    first.write_text("{}", encoding="utf-8")
    second = unique_path(tmp_path, "backup_2026", ".json")
    assert second == tmp_path / "backup_2026_3.json"


def test_unique_path_base_sorts_before_siblings(tmp_path):
    base = unique_path(tmp_path, "2026-07-15_backup", ".json")
    base.write_text("{}", encoding="utf-8")
    sibling = unique_path(tmp_path, "2026-07-15_backup", ".json")
    sibling.write_text("{}", encoding="utf-8")
    assert sorted([sibling.name, base.name])[0] == base.name
