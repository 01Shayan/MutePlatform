# 🗺️ Roadmap

Mute Platform is a **Decision Intelligence Platform** for VPN business management.

**Status legend:** Stable · Released · In Development · Planned · Deferred

Only **Released** / **Stable** versions are implemented. Everything else is planned,
in-progress, or deferred work.

---

## v0.1.0 — Released

**Workspace Foundation · Backup**

- Workspace-centric architecture
- Workspace Manager (add, edit, delete)
- Integration Registry
- PasarGuard Integration
- Secure Authentication
- Backup Module (frozen)
- Backup History · Delete Backup · Delete All Backups
- Per Workspace Storage · Per Workspace Logging
- Theme System · Modern CLI Interface

---

## v0.1.5 — Released

**Telegram Interface · Installation Experience**

- Owner-only Telegram bot (polling)
- Telegram Backup interface (create, history, delete, download)
- First-run Setup Wizard
- Automatic configuration migration
- Secrets kept out of JSON (`.env` only)

---

## v0.1.5.1 — Released

**Patch Release**

- Documentation and stability improvements on top of v0.1.5

---

## v0.1.6 — Released

**Engineering Hardening**

- Atomic JSON persistence
- Workspace registry recovery
- Workspace name validation
- Telegram workspace logging
- Unique history filenames
- Crash-safe persistence and workspace rename consistency
- Job lifecycle correctness
- Logging consistency between CLI and Telegram

---

## v0.2.0 — Released

**Group Checker**

Read-only analysis · integrity reports · group listing · user counts · invalid and empty group
detection · report generation, history, and export.

---

## v0.2.1 — Stable

**Telegram Workspace Management**

- Telegram Add / Edit / Delete Workspace (mirrors CLI)
- Cached workspace connection status
- Telegram Settings (reset tokens, bot token, owner IDs)
- Backup History Archive Details
- Temporary conversation cleanup

Stable foundation for the next major milestone.

---

## v0.3.0 — In Development

**Bulk Operations · Group Manager (architecture v1.2)**

```
Bulk Operations
  └── Group Manager
        ├── Group Catalog
        ├── Snapshot (RAM; Refresh Snapshot)
        ├── 🔎 Filter Users
        ├── 👥 View Matched Users
        └── 🛠 Actions → 📋 Review → 🚀 Execute → 📄 Report
```

- Telegram mirrors CLI exactly (shared copy / workflow).
- Dry Run removed; Execute only; mandatory Review + Confirm.
- Snapshot never auto-refreshes; manual Refresh clears filter / working set.
- Actions continue on failure; latest 3 reports retained.

---

## Migration — Deferred

**Migration** is a separate domain and is **deferred**.

It is not part of v0.3.0. It will be scheduled after the Groups module is stable.

---

## v0.4.0 — Planned

**Reports**

Business reports and statistics.

---

## v0.5.0 — Planned

**Analytics**

Business analytics and insights.

---

## v0.6.0 — Planned

**Additional Integrations**

Marzban · Hiddify · Marzneshin and beyond.

---

## v1.0.0 — Planned

**Stable Release**

Decision Intelligence Platform · AI-assisted recommendations · smart campaigns · revenue
prediction · customer segmentation · decision support for VPN operators.

---

## 🔌 Integrations

| Integration | Status |
|-------------|--------|
| PasarGuard | Released (v0.1.0) |
| Marzban | Planned |
| Hiddify | Planned |
| Marzneshin | Planned |

> **Golden Rule:** Build only what we need today, but build it in a way that doesn't need
> rewriting tomorrow.
