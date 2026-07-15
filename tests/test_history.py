import json

from mute.core.history import record_job


def test_record_job_writes_file(tmp_path):
    data = {
        "type": "backup",
        "status": "success",
        "panel": "PasarGuard",
        "profile": "Production",
        "users": 2130,
        "duration": 8.3,
    }
    path = record_job(data, jobs_dir=tmp_path)

    assert path.exists()
    assert path.name.endswith("_backup.json")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["type"] == "backup"
    assert payload["status"] == "success"
    assert payload["users"] == 2130
    assert "created_at" in payload


def test_repeated_records_never_overwrite(tmp_path):
    # Many records of the same type written back-to-back must each get a unique file.
    paths = [record_job({"type": "backup", "n": i}, jobs_dir=tmp_path) for i in range(5)]
    assert len({p.name for p in paths}) == 5
    for i, path in enumerate(paths):
        assert json.loads(path.read_text(encoding="utf-8"))["n"] == i


def test_history_files_sort_chronologically(tmp_path):
    paths = [record_job({"type": "backup"}, jobs_dir=tmp_path) for _ in range(3)]
    # The first record's filename sorts first (timestamp prefix, then numeric suffix).
    assert [p.name for p in paths] == sorted(p.name for p in paths)

