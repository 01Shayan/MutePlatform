# Changelog

All notable changes to Mute Platform are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

---

## v0.3.0 — In Development

### Changed

- Telegram Home now mirrors CLI branding (platform name, tagline, version, footer).
- Backup JSON schema simplified by removing unused runtime fields
  (`admin_id`, `on_hold_timeout`, `on_hold_expire_duration`, `next_plan`).
- Backup schema version incremented to `0.2`.
- Replaced **Group Engine** with **Bulk Operations → Group Manager**.
- Introduced **Working Set** (produced by Check; consumed by Actions).
- Manual user selection removed — Actions only run after a successful Check.
- Group Manager actions scaffolded: Add / Remove / Replace Group IDs (Coming Soon).

### Planned

- Add Group IDs
- Remove Group IDs
- Replace Group IDs
- Groups Foundation (as Bulk Operations expands)
- Groups History
- Shared Group Operation Engine (within Group Manager)

### Notes

- Active development milestone after the stable v0.2.1 line.
- Migration remains a separate deferred domain (not part of v0.3.0).

---

## v0.2.1

**Released**

### Added

- Telegram Add Workspace wizard (mirrors CLI)
- Telegram Edit Workspace
- Telegram Delete Workspace with confirmation
- Cached workspace connection status (Connected / Offline / Unknown)
- Telegram Settings: Reset Workspace Tokens, Change Bot Token, Change Owner IDs
- CLI Settings mirroring Telegram (same SettingsApplicationService)
- Telegram Backup History Archive Details (Download / Delete / Back)
- Temporary Telegram conversation cleanup (best-effort)

### Improved

- Workspace dashboard status no longer shows "Not checked"
- Telegram Workspace Management placeholders removed
- CLI and Telegram share one connection-status cache and identical status labels
- Successful/failed Backup connections update the shared status cache

### Notes

- Telegram remains a pure interface over the Service Layer.
- Bot token and owner ID changes require a manual bot restart.
- Connection status is cached; CLI verifies on dashboard open and persists the result for Telegram.
- Stable release line before v0.3.0 Groups development.

---

## v0.1.6

**Released**

### Added

- Atomic JSON persistence
- Workspace registry recovery
- Workspace name validation
- Telegram workspace logging
- Unique history filenames

### Improved

- Crash-safe persistence
- Workspace rename consistency
- Job lifecycle correctness
- Reliability of workspace storage
- Logging consistency between CLI and Telegram
- Added official systemd deployment template

### Notes

- This release introduces no new user-facing features.
- It focuses entirely on reliability, durability, and correctness before v0.2.0.

---

## v0.1.5

**Released**

### Added

- Telegram Interface (owner-only bot, polling)
- Telegram Backup Interface — Create Export, Backup History, Delete Single, Delete All, Download
- Live progress updates during export (a single edited message)
- First-Run Setup Wizard (Telegram Bot Token, Owner ID, Enable Telegram)
- Automatic configuration migration (versioned `config_version`)
- `.env`-only secret storage for `BOT_TOKEN`

### Improved

- Configuration layout: `settings.json` now stores only `config_version` and Telegram settings
- Installation experience: after cloning, running the app is enough — no manual config editing
- Documentation updated to v0.1.5 (README, ROADMAP, CHECKLIST)
- `requirements.txt` trimmed and pinned to the dependencies actually used

### Notes

- No changes to the frozen v0.1.0 Workspace Architecture, Backup module, or Service Layer.
- Telegram uses polling only — no webhook, reverse proxy, domain, or SSL required.
- Future updates require only `git pull`; configuration migrates automatically.

---

## v0.1.0

**Released**

### Added

- Workspace Architecture
- Workspace Manager
- Integration Registry
- PasarGuard Integration
- Secure Authentication
- Backup Module
- Backup History
- Delete Backup
- Delete All Backups
- Per Workspace Storage
- Per Workspace Logging
- Theme System
- Modern CLI Interface

### Fixed

- Rich rendering
- Workspace migration
- Backup synchronization
- UI consistency

### Notes

Version 0.1.0 is frozen. Only bug fixes are allowed.

---

## Versioning

| Bump | When |
|------|------|
| **Patch** | Bug fixes |
| **Minor** | New modules |
| **Major** | Platform milestones |
