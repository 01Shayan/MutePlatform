"""Synchronous PasarGuard REST API client.

Built on ``requests``. Authentication is transparent:

* If the profile has a username/password, the client obtains a bearer token via
  ``/api/admin/token`` on first use.
* A cached token is reused while it is still valid (JWT ``exp`` is inspected, with a small
  clock-skew margin).
* An expired token, or a ``401`` from any call, triggers one automatic re-authentication
  and retry (only when credentials are available).
* Whenever a new token is obtained, the optional ``on_token_refresh`` callback is invoked so
  the caller can persist it (e.g. back into the workspace).
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from typing import Any, Callable, Iterator, Optional, Protocol

import requests

from ...core.logging import get_logger
from .models import Token, User

logger = get_logger("api")


class Connection(Protocol):
    """The connection attributes the client needs — satisfied by ``Workspace``."""

    base_url: str
    verify_ssl: bool
    username: Optional[str]
    password: Optional[str]
    token: Optional[str]

    @property
    def has_credentials(self) -> bool: ...

TOKEN_PATH = "/api/admin/token"
CURRENT_ADMIN_PATH = "/api/admin"
USERS_PATH = "/api/users"

_CLOCK_SKEW_SECONDS = 30
_DEFAULT_PAGE_SIZE = 100


class PasarGuardError(Exception):
    """Base error for all PasarGuard client failures."""


class AuthenticationError(PasarGuardError):
    """Raised when authentication cannot be performed or fails."""


class APIError(PasarGuardError):
    """Raised for non-success HTTP responses."""

    def __init__(self, status_code: int, message: str, payload: Any = None) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message
        self.payload = payload


class PasarGuardClient:
    """A thin, typed wrapper over the PasarGuard REST API for a single panel."""

    def __init__(
        self,
        conn: Connection,
        *,
        timeout: float = 30.0,
        on_token_refresh: Callable[[str], None] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.conn = conn
        self.timeout = timeout
        self._on_token_refresh = on_token_refresh
        self._session = session or requests.Session()
        self._session.verify = conn.verify_ssl
        if conn.token:
            self._apply_token(conn.token)

    # -- authentication ---------------------------------------------------------------

    def authenticate(self) -> str:
        """Obtain a fresh bearer token using the profile's username/password."""
        if not self.conn.has_credentials:
            raise AuthenticationError(
                "No username/password available to authenticate. "
                "Provide credentials or a valid token."
            )

        logger.info("Connecting to %s", self.conn.base_url)
        try:
            response = self._session.post(
                self._url(TOKEN_PATH),
                data={
                    "username": self.conn.username,
                    "password": self.conn.password,
                    "grant_type": "password",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PasarGuardError(f"Network error during authentication: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError("Invalid username or password.")
        self._raise_for_status(response)

        token = Token.from_dict(response.json())
        self._apply_token(token.access_token)
        self.conn.token = token.access_token
        if self._on_token_refresh is not None:
            self._on_token_refresh(token.access_token)
        logger.info("Authentication successful")
        return token.access_token

    def _apply_token(self, token: str) -> None:
        self._session.headers["Authorization"] = f"Bearer {token}"

    def _ensure_token(self) -> None:
        """Make sure a usable token is present, refreshing proactively when possible."""
        token = self.conn.token
        if not token:
            self.authenticate()
            return
        if self.conn.has_credentials and _jwt_expired(token):
            logger.info("Cached token expired; refreshing.")
            self.authenticate()

    # -- request plumbing -------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
        _retry_on_auth: bool = True,
    ) -> Any:
        self._ensure_token()
        try:
            response = self._session.request(
                method,
                self._url(path),
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PasarGuardError(f"Network error calling {path}: {exc}") from exc

        if (
            response.status_code == 401
            and _retry_on_auth
            and self.conn.has_credentials
        ):
            logger.info("Received 401 on %s; re-authenticating and retrying once.", path)
            self.authenticate()
            return self._request(
                method, path, params=params, json_body=json_body, _retry_on_auth=False
            )

        self._raise_for_status(response)
        if not response.content:
            return None
        return response.json()

    def _url(self, path: str) -> str:
        return f"{self.conn.base_url}{path}"

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.ok:
            return
        payload: Any = None
        message = response.reason or "Request failed"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = str(payload.get("detail", message))
        except ValueError:
            payload = response.text or None
        raise APIError(response.status_code, message, payload)

    # -- endpoints --------------------------------------------------------------------

    def get_current_admin(self) -> dict:
        """Return the currently authenticated admin (also validates the token)."""
        return self._request("GET", CURRENT_ADMIN_PATH)

    def test_connection(self) -> dict:
        """Authenticate and confirm the panel is reachable. Returns the admin payload."""
        self._ensure_token()
        return self.get_current_admin()

    def get_users(self, *, offset: int = 0, limit: int = _DEFAULT_PAGE_SIZE) -> dict:
        """Return a single page of users: ``{"users": [...], "total": int}``."""
        return self._request(
            "GET", USERS_PATH, params={"offset": offset, "limit": limit}
        )

    def iter_users(self, *, page_size: int = _DEFAULT_PAGE_SIZE) -> Iterator[User]:
        """Yield every user, transparently paging through the API."""
        offset = 0
        while True:
            page = self.get_users(offset=offset, limit=page_size)
            batch = page.get("users", []) if isinstance(page, dict) else []
            if not batch:
                break
            for entry in batch:
                yield User.from_dict(entry)
            if len(batch) < page_size:
                break
            offset += page_size


def create_client(conn: Connection, *, timeout: float = 30.0) -> PasarGuardClient:
    """Build a client for a workspace connection, persisting refreshed tokens back to it."""
    on_refresh = getattr(conn, "save_token", None)
    return PasarGuardClient(conn, timeout=timeout, on_token_refresh=on_refresh)


def _jwt_expired(token: str, skew: int = _CLOCK_SKEW_SECONDS) -> bool:
    """Best-effort check of a JWT's ``exp`` claim without verifying the signature.

    Returns ``True`` only when the token is confidently past expiry. If the token cannot be
    decoded or has no ``exp``, returns ``False`` so a real request can decide (via 401).
    """
    parts = token.split(".")
    if len(parts) != 3:
        return False
    try:
        segment = parts[1]
        padded = segment + "=" * (-len(segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, binascii.Error, json.JSONDecodeError):
        return False
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return False
    return time.time() >= (exp - skew)
