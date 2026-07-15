"""Reusable Telegram temporary-conversation cleanup.

Interactive wizards track transient bot and user message IDs on the session.
When a workflow finishes or is cancelled, callers invoke ``cleanup_temporary``
so only the final UI message (``keep`` / ``last_message_id``) remains.

Cleanup is best-effort only — deletion failures never abort the caller.
"""

from __future__ import annotations

from .router import Router


def begin_temporary(router: Router, chat_id: int) -> None:
    """Start a new interactive workflow — discard any previous temporary IDs."""
    router.clear_temporary(chat_id)


def track_temporary(router: Router, chat_id: int, message_id: int | None) -> None:
    """Record a temporary bot or user message for later deletion."""
    router.track_temporary(chat_id, message_id)


async def cleanup_temporary(bot, router: Router, chat_id: int, *, keep: int | None = None) -> None:
    """Delete every tracked temporary message except ``keep``.

    ``keep`` defaults to the session's current UI message (``last_message_id``)
    so the final result / dashboard screen is preserved.

    Best-effort: Telegram/network failures are ignored per message so cleanup
    never raises to the caller or interrupts workflow completion.
    """
    session = router.session(chat_id)
    if keep is None:
        keep = session.last_message_id
    message_ids = router.pop_temporary(chat_id)
    for message_id in message_ids:
        if keep is not None and message_id == keep:
            continue
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:  # noqa: BLE001 — cleanup must never abort the workflow
            pass
