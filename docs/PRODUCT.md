# Product Definition — Bulk Operations · Group Manager

**Product:** Mute Platform  
**Milestone:** v0.3.0  
**Status:** In Development (`0.3.0-dev`)  
**Developer:** 01Shayan

---

## Purpose

**Bulk Operations** is the top-level home for every future bulk modification feature.

For this release it contains only:

```
Bulk Operations
  └── Group Manager
```

Group Manager manages users' Required Group IDs through Check → Working Set → Actions.

---

## Core concept — Working Set

Users are **never manually selected**.

1. Check inspects users (read-only).
2. Check produces a **Working Set** (matched, unmatched, statistics, criteria).
3. Every Action operates on that Working Set.

Actions must never perform another search.

---

## Group Manager flow

```
Check Group IDs
    ↓
Working Set (results)
    ↓
Actions
  ├── Add Group IDs
  ├── Remove Group IDs
  └── Replace Group IDs
```

Check is always the entry point. Add / Remove / Replace appear only after a successful Check.

---

## Product principles

- Telegram mirrors the CLI.
- Business logic lives in the Service Layer.
- Offline-first: Check prefers backups over live APIs.
- History stores metadata, not full datasets.
- Destructive or panel-changing operations require confirmation (Preview → Confirm → Execute).

---

## Out of scope (this milestone)

| Idea | Status |
|------|--------|
| Expire Manager | Future |
| Status Manager | Future |
| Data Limit Manager | Future |
| Manual / username selection | Removed by design |
| Migration | Deferred — separate domain |

---

## Next implementation steps

1. Add Group IDs  
2. Remove Group IDs  
3. Replace Group IDs  

No other Bulk Operations modules in this milestone.

---

## Related documents

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [ROADMAP.md](../ROADMAP.md)
- [CHECKLIST.md](../CHECKLIST.md)
- [CHANGELOG.md](../CHANGELOG.md)
