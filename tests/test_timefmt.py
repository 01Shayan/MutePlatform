from datetime import datetime, timedelta

from mute.core.timefmt import relative_time


def _ago(**kwargs):
    now = datetime(2026, 7, 10, 18, 0, 0)
    return relative_time(now - timedelta(**kwargs), now=now)


def test_relative_time_variants():
    assert _ago(seconds=15) == "15 seconds ago"
    assert _ago(seconds=1) == "1 second ago"
    assert _ago(minutes=3) == "3 minutes ago"
    assert _ago(minutes=1) == "1 minute ago"
    assert _ago(hours=2) == "2 hours ago"
    assert _ago(hours=1) == "1 hour ago"
    assert _ago(days=1) == "Yesterday"
    assert _ago(days=3) == "3 days ago"


def test_relative_time_old_date_shows_iso():
    now = datetime(2026, 7, 10, 18, 0, 0)
    moment = datetime(2026, 6, 1, 9, 0, 0)
    assert relative_time(moment, now=now) == "2026-06-01"


def test_relative_time_future_is_clamped():
    now = datetime(2026, 7, 10, 18, 0, 0)
    assert relative_time(now + timedelta(minutes=5), now=now) == "1 second ago"
