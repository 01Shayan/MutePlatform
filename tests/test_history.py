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
