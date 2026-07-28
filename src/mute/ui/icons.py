"""Approved emoji set — one icon per concept. Never invent alternatives."""

from __future__ import annotations


class Icon:
    """Canonical Design System icons (Mute Platform UI standard)."""

    # Navigation
    HOME = "🏠"
    BACK = "🔙"  # reserved; prefer HOME for "Back to parent" where product uses 🏠 Back
    CANCEL = "❌"
    CONFIRM = "✅"
    REFRESH = "🔄"

    # Managers / domains
    USERS = "👥"
    SNAPSHOT = "📸"
    GROUPS = "🏷️"
    REPORT = "📄"
    HISTORY = "🗂"
    SETTINGS = "⚙️"
    BACKUP = "📦"
    BULK = "🛠"
    MIGRATION = "🚚"
    WORKSPACES = "💼"
    BRAIN = "🧠"

    # Actions
    FILTER = "🔎"
    ADD = "➕"
    REMOVE = "➖"
    REPLACE = "🔁"
    ACTIONS = "🛠"
    REVIEW = "📋"
    DOWNLOAD = "⬇"
    EDIT = "✏"
    PAUSE = "⏸"
    ENABLE = "✅"

    # Status
    LOADING = "⏳"
    EXECUTING = "🚀"
    SUCCESS = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    DURATION = "⏱"

    # Legacy aliases used by older CLI screens (same glyph; do not invent new meanings)
    ERROR = FAILED
    PENDING = LOADING
    SEARCH = FILTER
    REPORTS = REPORT
    DELETE = "🗑️"
    PROFILE = "👤"
    API = "🌐"
    EXPORT = "💾"
    IMPORT = "📥"
    RESTORE = "♻️"
    SHIELD = "🛡"
    FOLDER = "📂"
    PANELS = "🏢"
    ANALYTICS = "📈"
    MARKETING = "🎯"
    CAMPAIGN = "🎁"
