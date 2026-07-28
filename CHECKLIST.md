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

## v0.3.0 — Bulk Operations · Group Manager

**Status:** In Development  
**Version file:** `0.3.0-dev`

### Architecture

- [x] Bulk Operations top-level module
- [x] Group Manager under Bulk Operations
- [x] Working Set (replaces manual selection)
- [x] Check → Working Set → Actions flow (CLI + Telegram)
- [x] Action plugins scaffolded (Add / Remove / Replace)

### Check

- [x] Check Group IDs (Required Groups) — behaviour preserved
- [x] Working Set includes matched / unmatched / statistics / criteria

### Actions (next)

- [ ] Add Group IDs
- [ ] Remove Group IDs
- [ ] Replace Group IDs

### Quality

- [ ] Action implementation tests
- [ ] Documentation kept in sync
- [ ] Architecture compliance review
- [ ] Production validation before freeze

### Out of scope for v0.3.0

- [ ] Additional Bulk Operations managers (Expire, Status, …)
- [ ] Migration (deferred)
- [ ] Manual user selection (removed by design)
