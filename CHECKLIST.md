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

## v0.3.0 — Groups Module

**Status:** In Development  
**Version file:** `0.3.0-dev`

### Foundation

- [ ] Groups Foundation
- [ ] Shared Group Operation Engine
- [ ] Service Layer DTOs and interfaces (CLI + Telegram)
- [ ] Offline-first / backup-as-source-of-truth where applicable

### Check

- [ ] Groups Check — queries and analysis
- [ ] Integrity / required-groups workflows
- [ ] CLI Check screens
- [ ] Telegram Check screens

### Modify

- [ ] Groups Modify — mutation workflows
- [ ] Confirmation for destructive or panel-changing operations
- [ ] CLI Modify screens
- [ ] Telegram Modify screens

### History

- [ ] Groups History — metadata history (not full datasets)
- [ ] Logging for group operations
- [ ] CLI History screens
- [ ] Telegram History screens

### Quality

- [ ] Tests (service + CLI + Telegram)
- [ ] Documentation (README · CHANGELOG · ROADMAP · PRODUCT)
- [ ] Architecture compliance review
- [ ] Production validation before freeze

### Out of scope for v0.3.0

- [ ] Migration (deferred — separate domain)
- [ ] Reports / Analytics (later milestones)
