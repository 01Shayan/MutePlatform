# ✅ Development Checklist

Tracks progress per version.

---

## Released (summary)

| Version | Focus | Status |
|---------|--------|--------|
| v0.1.0 | Workspace Foundation · Backup | Frozen |
| v0.1.5 | Telegram Interface · Installation | Released |
| v0.1.5.1 | Patch | Released |
| v0.1.6 | Engineering Hardening | Released |
| v0.2.0 | Group Checker | Released |
| v0.2.1 | Telegram Workspace Management | Stable |

---

## v0.3.0 — Bulk Operations · Group Manager (architecture v1.2)

**Status:** In Development  
**Version file:** `0.3.0-dev`

### Architecture

- [x] Telegram mirrors CLI (shared labels / workflow)
- [x] Group Catalog + Snapshot (RAM only)
- [x] 🔎 Filter Users / 👥 View Matched Users / 🔄 Refresh Snapshot
- [x] Unified 📋 Review → ✅ Confirm → 🚀 Execute
- [x] Dry Run removed
- [x] Execution Report (rolling latest 3)
- [x] CLI + Telegram wired

### Actions

- [x] ➕ Add Groups
- [x] ➖ Remove Groups
- [x] 🔁 Replace Groups

## Design System (v1.0)

- [x] Shared `mute.ui` package (icons + copy + layout)
- [x] CLI and Telegram consume the same labels
- [x] Terminology: Matched Users (UI) / Working Set (code)
- [x] `docs/DESIGN_SYSTEM.md`
- [ ] Remaining wizard / long-form confirm copy migration (optional polish)

### Out of scope for v0.3.0

- [ ] Additional managers (Expire, Status, …)
- [ ] Migration (deferred)
