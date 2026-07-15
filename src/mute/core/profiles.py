"""Panel connection profiles and their on-disk store.

A :class:`Profile` describes how to reach a single PasarGuard panel. Multiple profiles let a
user back up one panel and migrate into another. Profiles are the primary configuration
source; ``.env`` only supplies default values when creating a new profile.

For v0.1 the store lives inside the project at ``config/profiles.json`` (git-ignored, since
it may hold credentials and cached tokens). Global/shared profiles may come later. The store
also remembers which profile is currently *active*.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .logging import get_logger
from .paths import PROFILES_PATH

logger = get_logger("profiles")

DEFAULT_STORE_PATH = PROFILES_PATH

_PERSISTED_FIELDS = ("name", "base_url", "username", "password", "token", "verify_ssl")


@dataclass
class Profile:
    """Connection details for a single PasarGuard panel."""

    name: str
    base_url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    @property
    def has_credentials(self) -> bool:
        """True if username/password are available for (re)authentication."""
        return bool(self.username and self.password)

    @property
    def auth_method(self) -> str:
        if self.has_credentials:
            return "username/password"
        if self.token:
            return "token"
        return "none"

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(**{key: data.get(key) for key in _PERSISTED_FIELDS if key in data})

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if key in _PERSISTED_FIELDS}


@dataclass
class ProfileStore:
    """Loads, persists, and manages :class:`Profile` objects on disk."""

    path: Path = DEFAULT_STORE_PATH
    _profiles: dict[str, Profile] = field(default_factory=dict, init=False)
    _active: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.load()

    # -- persistence ------------------------------------------------------------------

    def load(self) -> None:
        self._profiles = {}
        self._active = None
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read profile store %s: %s", self.path, exc)
            return
        for entry in raw.get("profiles", []):
            try:
                profile = Profile.from_dict(entry)
            except TypeError as exc:
                logger.warning("Skipping malformed profile entry: %s", exc)
                continue
            self._profiles[profile.name] = profile
        active = raw.get("active")
        self._active = active if active in self._profiles else None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active": self._active,
            "profiles": [p.to_dict() for p in self._profiles.values()],
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError as exc:  # best-effort on platforms without chmod semantics
            logger.debug("Could not set permissions on %s: %s", self.path, exc)

    # -- queries ----------------------------------------------------------------------

    def list(self) -> list[Profile]:
        return list(self._profiles.values())

    def names(self) -> list[str]:
        return list(self._profiles.keys())

    def is_empty(self) -> bool:
        return not self._profiles

    def exists(self, name: str) -> bool:
        return name in self._profiles

    def get(self, name: str) -> Profile | None:
        return self._profiles.get(name)

    @property
    def active_name(self) -> str | None:
        return self._active

    def get_active(self) -> Profile | None:
        if self._active is None:
            return None
        return self._profiles.get(self._active)

    # -- mutations --------------------------------------------------------------------

    def upsert(self, profile: Profile, *, make_active: bool = False) -> None:
        self._profiles[profile.name] = profile
        if make_active or self._active is None:
            self._active = profile.name
        self.save()

    def rename(self, old_name: str, new_name: str) -> None:
        profile = self._profiles.pop(old_name, None)
        if profile is None:
            return
        profile.name = new_name
        self._profiles[new_name] = profile
        if self._active == old_name:
            self._active = new_name
        self.save()

    def delete(self, name: str) -> bool:
        if name not in self._profiles:
            return False
        del self._profiles[name]
        if self._active == name:
            self._active = next(iter(self._profiles), None)
        self.save()
        return True

    def set_active(self, name: str) -> bool:
        if name not in self._profiles:
            return False
        self._active = name
        self.save()
        return True

    def set_token(self, name: str, token: str) -> None:
        """Persist a freshly obtained bearer token for a profile."""
        profile = self._profiles.get(name)
        if profile is None:
            return
        profile.token = token
        self.save()
