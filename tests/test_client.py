import base64
import json
import time

from mute.integrations.pasarguard.client import _jwt_expired


def _jwt(exp_offset: int) -> str:
    payload = {"exp": int(time.time()) + exp_offset}
    segment = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{segment}.signature"


def test_expired_token_detected():
    assert _jwt_expired(_jwt(-100)) is True


def test_valid_token_not_expired():
    assert _jwt_expired(_jwt(3600)) is False


def test_garbage_token_is_not_flagged_expired():
    assert _jwt_expired("not-a-jwt") is False
    assert _jwt_expired("a.b.c") is False


def test_token_without_exp_not_flagged():
    segment = base64.urlsafe_b64encode(json.dumps({"sub": "admin"}).encode()).decode().rstrip("=")
    assert _jwt_expired(f"h.{segment}.s") is False
