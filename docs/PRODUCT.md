# Product Definition — Bulk Operations · Group Manager

**Product:** Mute Platform  
**Milestone:** v0.3.0  
**Status:** In Development (`0.3.0-dev`)  
**Developer:** 01Shayan  
**Architecture:** Bulk Operations v1.2 (final)

---

## Mirror Principle

CLI is the reference implementation. Telegram is an exact mirror of CLI
(menus, workflow, labels, confirmation). Only presentation differs.

---

## Purpose

**Bulk Operations** is a collection of completely independent managers.

```
Bulk Operations
│
├── Group Manager
├── Status Manager   (future)
├── Expire Manager   (future)
├── Data Limit Manager (future)
└── …
```

---

## Group Manager Home

```
👥 Group Manager — MuteVPN
📸 Snapshot Users: 1432
🏷️ Available Groups: 18
👥 Working Set: 1432 matched
────────────────────
🔎 Filter Users
👥 View Matched Users
🔄 Refresh Snapshot
🏠 Back
```

---

## Lifecycle (v1.3)

```
Enter → Catalog + Snapshot
↓
🎯 Select Target Users (Rule Builder)
  · 🌐 All Snapshot Users
  · 🏷 Users with Groups
  · 🚫 Users without Groups
↓
👥 View Matched Users → 🛠 Action
↓
📋 Review (plain English) → ✅ Confirm
↓
🚀 Execute → 📄 Report
```

UI never exposes Include / Exclude / ANY / ALL. Query Engine unchanged.

---

## Snapshot rules

- RAM only; never on disk  
- Immutable by default; never auto-refreshed  
- New Snapshot only via **🔄 Refresh Snapshot** or re-entering Group Manager  

---

## Related documents

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)
- [ROADMAP.md](../ROADMAP.md)
- [CHECKLIST.md](../CHECKLIST.md)
- [CHANGELOG.md](../CHANGELOG.md)
