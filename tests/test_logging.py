from mute.core.logging import get_logger, use_workspace
from mute.core.workspace import Workspace


def test_logs_write_to_workspace_folder(tmp_path):
    ws = Workspace(name="Prod", integration="pasarguard", base_url="https://x", root=tmp_path)
    ws.ensure_dirs()
    use_workspace(ws.logs_dir)

    get_logger("backup").info("Backup completed.")
    get_logger("api").info("Authentication successful")

    assert (ws.logs_dir / "backup.log").exists()
    assert (ws.logs_dir / "api.log").exists()
    assert "Backup completed" in (ws.logs_dir / "backup.log").read_text(encoding="utf-8")
