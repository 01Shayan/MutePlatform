"""Workspaces — the primary entity of the platform.

A **Workspace** is one complete working environment: an integration, its connection settings,
and all of its own data (backups, migrations, reports, exports, logs, cache, history). Modules
always operate on a Workspace — never on a raw connection profile.

On disk::

    config/workspaces.json          # registry: {"active": name, "workspaces": [names]}
    workspaces/
        <name>/
            workspace.json          # integration + connection settings
            backups/  migrations/  reports/  exports/  logs/  cache/  history/

``workspace.json`` and the connection it holds may contain credentials/tokens, so the whole
``workspaces/`` tree is git-ignored.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .integrations import integration_name, resolve_integration_key
from .jsonio import write_json_atomic
from .logging import get_logger
from .paths import BACKUPS_DIR, WORKSPACES_DIR, WORKSPACES_PATH

logger = get_logger("app")

# Connection fields persisted inside workspace.json (besides workspace_name + integration).
_CONNECTION_FIELDS = ("base_url", "username", "password", "token", "verify_ssl")

# The per-workspace data folders that are always created.
_SUBDIRS = ("backups", "migrations", "reports", "exports", "logs", "cache", "history")

# Characters that are illegal in a workspace name (path separators and Windows-reserved chars).
_ILLEGAL_CHARS = '/\\:*?"<>|'

# Windows reserved device names — rejected so a workspace can never map to a special file.
_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


class InvalidWorkspaceName(ValueError):
    """Raised when a workspace name is unsafe or would collide with another workspace."""


def validate_workspace_name(name: str) -> str:
    """Return the trimmed name if it is a safe filesystem identifier, else raise.

    Rejects empty/whitespace names, ``.`` and ``..``, path separators (traversal), control
    characters, names that are only dots/spaces, and Windows reserved device names.
    """
    cleaned = (name or "").strip()
    if not cleaned:
        raise InvalidWorkspaceName("Workspace name cannot be empty.")
    if cleaned in {".", ".."}:
        raise InvalidWorkspaceName("Workspace name cannot be '.' or '..'.")
    if "/" in cleaned or "\\" in cleaned:
        raise InvalidWorkspaceName("Workspace name cannot contain '/' or '\\'.")
    if any(ord(ch) < 32 for ch in cleaned):
        raise InvalidWorkspaceName("Workspace name cannot contain control characters.")
    if any(ch in _ILLEGAL_CHARS for ch in cleaned):
        raise InvalidWorkspaceName('Workspace name cannot contain any of : * ? " < > |')
    if set(cleaned) <= {".", " "}:
        raise InvalidWorkspaceName("Workspace name cannot consist only of dots or spaces.")
    if cleaned.split(".", 1)[0].lower() in _RESERVED_NAMES:
        raise InvalidWorkspaceName(f"'{cleaned}' is a reserved name.")
    return cleaned


def _safe_dirname(name: str) -> str:
    """Turn a workspace name into a filesystem-safe directory name.

    Validated names (see :func:`validate_workspace_name`) map to themselves, so directories stay
    human-readable and stable. This remains a defensive net that never returns ``""``, ``.`` or
    ``..`` even for un-validated legacy input.
    """
    cleaned = "".join("_" if ch in _ILLEGAL_CHARS else ch for ch in name).strip()
    if not cleaned or set(cleaned) <= {"."}:
        return "workspace"
    return cleaned


def _dir_key(name: str) -> str:
    """The case-insensitive directory identity of a name, for collision detection."""
    return _safe_dirname(name).casefold()


# Per-workspace backup settings (defaults for new and legacy manifests).
DEFAULT_MAX_BACKUPS = 10
DEFAULT_AUTO_BACKUP_ENABLED = False
DEFAULT_AUTO_BACKUP_INTERVAL = 0  # minutes; 0 means unset while disabled


@dataclass
class Workspace:
    """One working environment: an integration + connection + its own data folders."""

    name: str
    integration: str  # integration key, e.g. "pasarguard"
    base_url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    verify_ssl: bool = True
    created_at: str | None = None
    auto_backup_enabled: bool = DEFAULT_AUTO_BACKUP_ENABLED
    auto_backup_interval: int = DEFAULT_AUTO_BACKUP_INTERVAL
    max_backups: int = DEFAULT_MAX_BACKUPS
    root: Path = field(default=WORKSPACES_DIR, repr=False)
    _store: "WorkspaceStore | None" = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.root = Path(self.root)
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    # -- connection interface (consumed by integration clients) -----------------------

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    @property
    def auth_method(self) -> str:
        if self.has_credentials:
            return "username/password"
        if self.token:
            return "token"
        return "none"

    def save_token(self, token: str) -> None:
        """Persist a freshly obtained token (called by the client on refresh)."""
        self.token = token
        if self._store is not None:
            self._store.set_token(self.name, token)

    # -- folders ----------------------------------------------------------------------

    @property
    def dir(self) -> Path:
        return self.root / _safe_dirname(self.name)

    @property
    def manifest_path(self) -> Path:
        return self.dir / "workspace.json"

    @property
    def backups_dir(self) -> Path:
        return self.dir / "backups"

    @property
    def migrations_dir(self) -> Path:
        return self.dir / "migrations"

    @property
    def reports_dir(self) -> Path:
        return self.dir / "reports"

    @property
    def exports_dir(self) -> Path:
        return self.dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.dir / "logs"

    @property
    def cache_dir(self) -> Path:
        return self.dir / "cache"

    @property
    def history_dir(self) -> Path:
        return self.dir / "history"

    def ensure_dirs(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for sub in _SUBDIRS:
            (self.dir / sub).mkdir(exist_ok=True)
        self._write_readme()

    def _write_readme(self) -> None:
        readme = self.dir / "README.md"
        if readme.exists():
            return
        created = (self.created_at or "")[:10]
        lines = [
            "Workspace",
            self.name,
            "",
            "Integration",
            integration_name(self.integration),
            "",
            "Created",
            created,
            "",
            "This directory contains:",
            "",
            "• backups",
            "• migrations",
            "• reports",
            "• exports",
            "• logs",
            "• cache",
            "• history",
            "",
        ]
        readme.write_text("\n".join(lines), encoding="utf-8")

    # -- persistence ------------------------------------------------------------------

    def to_dict(self) -> dict:
        data = {
            "workspace_name": self.name,
            "integration": integration_name(self.integration),
        }
        data.update({key: getattr(self, key) for key in _CONNECTION_FIELDS})
        data["created_at"] = self.created_at
        data["auto_backup_enabled"] = bool(self.auto_backup_enabled)
        data["auto_backup_interval"] = int(self.auto_backup_interval)
        data["max_backups"] = int(self.max_backups)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Workspace":
        raw_integration = data.get("integration", "pasarguard")
        return cls(
            name=data.get("workspace_name") or data.get("name") or "workspace",
            integration=resolve_integration_key(raw_integration),
            base_url=data.get("base_url", ""),
            username=data.get("username"),
            password=data.get("password"),
            token=data.get("token"),
            verify_ssl=bool(data.get("verify_ssl", True)),
            created_at=data.get("created_at"),
            auto_backup_enabled=bool(data.get("auto_backup_enabled", DEFAULT_AUTO_BACKUP_ENABLED)),
            auto_backup_interval=int(
                data.get("auto_backup_interval", DEFAULT_AUTO_BACKUP_INTERVAL) or 0
            ),
            max_backups=int(data.get("max_backups", DEFAULT_MAX_BACKUPS) or DEFAULT_MAX_BACKUPS),
        )


@dataclass
class WorkspaceStore:
    """Loads, persists, and manages :class:`Workspace` objects on disk."""

    root: Path = WORKSPACES_DIR
    registry_path: Path = WORKSPACES_PATH
    _names: list[str] = field(default_factory=list, init=False)
    _active: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.registry_path = Path(self.registry_path)
        self.load()

    # -- registry ---------------------------------------------------------------------

    def load(self) -> None:
        self._names = []
        self._active = None
        if not self.registry_path.exists():
            self._recover_from_disk()
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Workspace registry %s is unreadable (%s); recovering from disk.",
                self.registry_path, exc,
            )
            self._recover_from_disk()
            return
        self._names = [n for n in raw.get("workspaces", []) if isinstance(n, str)]
        active = raw.get("active")
        self._active = active if active in self._names else None

    def _recover_from_disk(self) -> None:
        """Rebuild the registry by scanning ``workspaces/*/workspace.json``.

        A corrupted or missing registry must never silently lose every workspace. Each manifest's
        recorded name is trusted; the recovered registry is persisted so recovery happens once.
        The active workspace is not recorded in manifests, so the first recovered name is used.
        """
        if not self.root.exists():
            return
        recovered: list[str] = []
        for child in sorted(self.root.iterdir()):
            manifest = child / "workspace.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping unreadable manifest %s: %s", manifest, exc)
                continue
            name = data.get("workspace_name") or data.get("name")
            if isinstance(name, str) and name and name not in recovered:
                recovered.append(name)
        if not recovered:
            return
        self._names = recovered
        self._active = recovered[0]
        logger.warning("Recovered %d workspace(s) from disk.", len(recovered))
        self._save_registry()

    def _save_registry(self) -> None:
        payload = {"active": self._active, "workspaces": self._names}
        write_json_atomic(self.registry_path, payload)

    def _write_manifest(self, workspace: Workspace) -> None:
        write_json_atomic(workspace.manifest_path, workspace.to_dict(), mode=0o600)

    # -- queries ----------------------------------------------------------------------

    def names(self) -> list[str]:
        return list(self._names)

    def is_empty(self) -> bool:
        return not self._names

    def exists(self, name: str) -> bool:
        return name in self._names

    def dir_is_free(self, name: str, *, current: str | None = None) -> bool:
        """True if ``name`` does not collide with another workspace's directory.

        Collision is checked on the case-insensitive directory identity so two distinct names can
        never resolve to (or, on case-insensitive filesystems, share) the same folder.
        """
        key = _dir_key(name)
        return not any(
            existing != current and _dir_key(existing) == key for existing in self._names
        )

    def get(self, name: str) -> Workspace | None:
        if name not in self._names:
            return None
        manifest = self.root / _safe_dirname(name) / "workspace.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read workspace '%s': %s", name, exc)
            return None
        workspace = Workspace.from_dict(data)
        workspace.root = self.root
        workspace._store = self
        return workspace

    def list(self) -> list[Workspace]:
        return [ws for ws in (self.get(name) for name in self._names) if ws is not None]

    @property
    def active_name(self) -> str | None:
        return self._active

    def get_active(self) -> Workspace | None:
        return self.get(self._active) if self._active else None

    # -- mutations --------------------------------------------------------------------

    def create(self, workspace: Workspace, *, make_active: bool = False) -> Workspace:
        workspace.name = validate_workspace_name(workspace.name)
        if not self.dir_is_free(workspace.name):
            raise InvalidWorkspaceName(
                f"'{workspace.name}' collides with an existing workspace directory."
            )
        workspace.root = self.root
        workspace._store = self
        workspace.ensure_dirs()
        self._write_manifest(workspace)
        if workspace.name not in self._names:
            self._names.append(workspace.name)
        if make_active or self._active is None:
            self._active = workspace.name
        self._save_registry()
        return workspace

    def save(self, workspace: Workspace) -> None:
        """Persist connection changes (e.g. a refreshed token) for a workspace."""
        workspace.root = self.root
        workspace._store = self
        workspace.ensure_dirs()
        self._write_manifest(workspace)

    def rename(self, old_name: str, new_name: str) -> bool:
        """Rename a workspace, moving its data folder and keeping the manifest consistent.

        Returns ``False`` on conflict. After a successful rename the manifest's ``workspace_name``
        always matches the registry, so a later ``get(new_name)`` never returns stale metadata.
        """
        if old_name not in self._names:
            return False
        new_name = validate_workspace_name(new_name)
        if new_name != old_name and not self.dir_is_free(new_name, current=old_name):
            return False
        old_dir = self.root / _safe_dirname(old_name)
        new_dir = self.root / _safe_dirname(new_name)
        if new_dir != old_dir:
            if new_dir.exists():
                return False
            if old_dir.exists():
                old_dir.rename(new_dir)
        self._names = [new_name if n == old_name else n for n in self._names]
        if self._active == old_name:
            self._active = new_name
        self._save_registry()
        self._rewrite_manifest_name(new_name)
        return True

    def _rewrite_manifest_name(self, name: str) -> None:
        """Update the on-disk manifest's ``workspace_name`` so it matches the registry."""
        manifest = self.root / _safe_dirname(name) / "workspace.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if data.get("workspace_name") == name:
            return
        data["workspace_name"] = name
        write_json_atomic(manifest, data, mode=0o600)

    def set_token(self, name: str, token: str) -> None:
        workspace = self.get(name)
        if workspace is None:
            return
        workspace.token = token
        self._write_manifest(workspace)

    def set_active(self, name: str) -> bool:
        if name not in self._names:
            return False
        self._active = name
        self._save_registry()
        return True

    def delete(self, name: str) -> bool:
        if name not in self._names:
            return False
        target = self.root / _safe_dirname(name)
        shutil.rmtree(target, ignore_errors=True)
        self._names.remove(name)
        if self._active == name:
            self._active = self._names[0] if self._names else None
        self._save_registry()
        return True


def bootstrap(store: WorkspaceStore) -> None:
    """One-time setup: migrate legacy profiles (or seed from .env), then upgrade scaffolding."""
    if store.is_empty():
        from .profiles import ProfileStore

        profiles = ProfileStore()
        if not profiles.is_empty():
            logger.info("Migrating %d profile(s) into workspaces…", len(profiles.list()))
            for profile in profiles.list():
                store.create(
                    _workspace_from_connection(profile),
                    make_active=(profile.name == profiles.active_name),
                )
            _migrate_legacy_backups(store, profiles.active_name or store.names()[0])
            return

        from .config import env_defaults

        defaults = env_defaults()
        if defaults is not None:
            store.create(_workspace_from_connection(defaults), make_active=True)
        return

    _upgrade_existing(store)


def _upgrade_existing(store: WorkspaceStore) -> None:
    """Bring pre-freeze workspaces up to the current scaffold (README + manifest format)."""
    for name in store.names():
        workspace = store.get(name)
        if workspace is None:
            continue
        store.save(workspace)  # normalize manifest (integration display name, folders)


def _workspace_from_connection(conn) -> Workspace:
    return Workspace(
        name=conn.name,
        integration="pasarguard",
        base_url=conn.base_url,
        username=conn.username,
        password=conn.password,
        token=conn.token,
        verify_ssl=conn.verify_ssl,
    )


def _migrate_legacy_backups(store: WorkspaceStore, target_name: str | None) -> None:
    """Move a pre-workspace global ``backups/`` folder into its workspace."""
    if not target_name or not BACKUPS_DIR.exists():
        return
    workspace = store.get(target_name)
    if workspace is None:
        return
    destination = workspace.backups_dir
    destination.mkdir(parents=True, exist_ok=True)
    for item in list(BACKUPS_DIR.iterdir()):
        target = destination / item.name
        if target.exists():
            continue
        try:
            shutil.move(str(item), str(target))
        except OSError as exc:
            logger.warning("Could not migrate backup '%s': %s", item.name, exc)
    try:
        BACKUPS_DIR.rmdir()
    except OSError:
        pass  # not empty (partial migration) — leave it be
    logger.info("Migrated legacy backups into workspace '%s'.", target_name)
