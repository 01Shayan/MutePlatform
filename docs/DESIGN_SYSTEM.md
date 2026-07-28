# Design System — Mute Platform UI/UX Standard

**Version:** 1.0  
**Status:** Active  

CLI is the reference. Telegram is an exact mirror. Only rendering differs.

## Shared package

All user-facing labels live in:

- `src/mute/ui/icons.py` — approved emoji set  
- `src/mute/ui/copy.py` — platform-wide copy  
- `src/mute/ui/layout.py` — divider + screen layout helper  

Do not hardcode menu labels, buttons, or status messages in screens/handlers.

## Terminology

| UI term | Internal (code OK) |
|---------|-------------------|
| Matched Users | Working Set |
| Select Target Users | Query / Filter |
| All selected groups | MatchMode.ALL |
| Any selected group | MatchMode.ANY |
| Users without groups | exclude_group_ids |
| Refresh Snapshot | refresh_snapshot |

One concept → one UI name. Never show Include / Exclude / ANY / ALL in the UI.

## Screen layout

```
Title
Summary
────────────────────
Content
────────────────────
Actions / Navigation
```

## Navigation buttons

- `🏠 Back`
- `❌ Cancel`
- `✅ Confirm`
- `🔄 Refresh Snapshot`

## Status tone

- `⏳ Loading...`
- `🚀 Executing...`
- `✅ Operation completed successfully.`
- `❌ Operation failed.`
- `⚠️ …`
- `ℹ️ …`

## Selection Rule

Whenever the application already knows the available values, users must select them from a shared selector component.

Users must never manually type identifiers for known entities.

This rule applies to Groups, Statuses, Workspaces, Tags, Locations, and any future selectable entities.

Shared selectors live under `src/mute/ui/components/` (e.g. `group_selector.py`). CLI is the reference; Telegram mirrors the same selection experience.

## Mirror rule

Every CLI screen must have a Telegram equivalent with the same titles, wording, ordering, and confirmation flow.
