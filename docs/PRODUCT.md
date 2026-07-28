# Product Definition — Groups Module

**Product:** Mute Platform  
**Milestone:** v0.3.0  
**Status:** In Development (`0.3.0-dev`)  
**Developer:** 01Shayan

---

## Purpose

The **Groups** module is the next major workspace capability after Backup and the
early Group Checker release.

It turns group operations into a first-class domain:

```
Groups
  ├── Check
  ├── Modify
  └── History
```

Operators use Groups to understand panel group membership, apply controlled changes,
and keep an auditable history — through both CLI and Telegram.

---

## Product principles

- Telegram mirrors the CLI (same capabilities; UI may differ).
- All business logic lives in the Service Layer.
- Offline-first where practical: analysis prefers backups over live APIs.
- Backup remains the preferred source of truth for Check-style analysis.
- History stores metadata, not full datasets.
- Destructive or panel-changing operations require confirmation.
- One shared engine powers group operations — no duplicated CLI/Telegram logic.

---

## Scope (v0.3.0)

### Groups Foundation

Workspace-aware Groups entry point, models, and navigation shared by all
sub-features.

### Groups Check

Read / analyze group membership and related conditions (for example required
groups, integrity, matching users). Prefer backup-based analysis.

### Groups Modify

Apply group-related changes through the Service Layer with explicit confirmation
and clear results.

### Groups History

Record operation metadata per workspace (what ran, when, outcome). Not a dump of
full user payloads.

### Shared Group Operation Engine

Single engine used by Check and Modify so computation and rules are implemented
once and reused by every interface.

---

## Out of scope (v0.3.0)

| Domain | Status |
|--------|--------|
| Migration | Deferred — separate domain |
| Reports | Later milestone |
| Analytics | Later milestone |
| Additional panel integrations | Later milestone |

---

## Interfaces

| Interface | Role |
|-----------|------|
| CLI | Reference behaviour |
| Telegram | Exact functional mirror |

Both call the same Groups services. Neither owns business rules.

---

## Success criteria

- Operators can Check, Modify, and review History for groups inside a workspace.
- CLI and Telegram expose the same capabilities.
- Group logic is centralized in services / the shared engine.
- Tests and docs ship with the feature set.
- Migration is not started as part of this milestone.

---

## Related documents

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [ROADMAP.md](../ROADMAP.md)
- [CHECKLIST.md](../CHECKLIST.md)
- [CHANGELOG.md](../CHANGELOG.md)
