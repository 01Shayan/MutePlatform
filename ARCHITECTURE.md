# Mute Platform
# ARCHITECTURE.md

> This document defines the engineering philosophy, architecture, and development rules of Mute Platform.
>
> Every implementation must follow this document.
>
> If code conflicts with these principles, preserve the architecture instead of introducing inconsistent implementations.

---

# Vision

Mute Platform is an engineering-first VPN Operations Platform.

The project prioritizes:

- Simplicity
- Maintainability
- Consistency
- Reliability
- Long-term scalability

Architecture always has higher priority than implementation speed.

---

# Core Philosophy

Simple.

Predictable.

Consistent.

Extensible.

Every release should make the platform stronger,
not more complicated.

---

# Golden Rules

## 1. Telegram mirrors the CLI

Telegram is an exact mirror of the CLI.

Features must exist in both interfaces.

Only the UI may differ.

Business capabilities must remain identical.

---

## 2. Business Logic belongs to the Service Layer

Business logic never belongs inside:

- CLI
- Telegram
- Screens
- Handlers
- Routers

Interfaces only call services.

---

## 3. Single Source of Truth

Business logic is implemented once.

Never duplicate logic between interfaces.

---

## 4. Extend before Redesign

Prefer extending existing components.

Do not redesign architecture without a strong engineering reason.

---

## 5. Preserve Architecture

Before implementing any feature ask:

Does this fit the current architecture?

If yes:

extend it.

Do not redesign it.

---

## 6. One Goal per Release

Every release has one primary goal.

Avoid feature creep.

---

## 7. No Scope Creep

Do not add unrelated features during the implementation of another release.

---

## 8. Offline First

Whenever possible:

operate from backups,

not live APIs.

---

## 9. Backup is the Source of Truth

Group Checker

Reports

Analytics

must operate from backups whenever possible.

---

## 10. Compute Once

Compute data once.

Reuse the computed result.

Never execute the same expensive operation twice.

---

## 11. History is Metadata

History stores metadata.

Not complete datasets.

---

## 12. Logging Everywhere

Every major feature must provide:

- logging
- history
- tests

---

## 13. Every Feature Requires Tests

No feature is complete without automated tests.

---

## 14. Documentation is Part of the Release

Every release updates:

- README
- CHANGELOG
- ROADMAP
- CHECKLIST
- Version

---

## 15. Architecture before Features

Design first.

Implementation second.

---

## 16. CLI is the Reference Interface

The CLI defines behaviour.

Telegram mirrors it.

---

## 17. DTO Boundary

Interfaces only consume DTOs.

Never expose:

- filesystem
- raw JSON
- internal models

---

## 18. Stateless Services

Services should remain stateless whenever possible.

---

## 19. Configuration Rules

Secrets belong to:

.env

Configuration belongs to:

config/

Never mix them.

---

## 20. Atomic Persistence

Every persistent write must be atomic.

---

## 21. Validate Before Save

Every input must be validated before persistence.

---

## 22. Confirm Destructive Operations

Delete

Reset

Remove

always require confirmation.

---

## 23. Stable Means Stable

Stable releases must not contain unfinished placeholders.

---

## 24. Workspace Isolation

Every workspace owns its own:

- logs
- backups
- history
- exports

---

## 25. Consistency over Cleverness

Readable code is preferred over clever code.

---

## 26. Reuse before Create

Always check whether an existing component can be reused.

---

## 27. Platform Mindset

Mute Platform is a platform,

not a collection of scripts.

---

## 28. Future without Overengineering

Design for future growth,

but implement only today's requirements.

---

## 29. Engineering Reports

Every feature concludes with an engineering report.

---

## 30. Git Operations

AI assistants must never:

- commit
- push
- tag
- create releases

Only the project owner performs Git operations.

---

## 31. Preserve Product Identity

Product:

Mute Platform

Developer:

01Shayan

---

## 32. Workspace Philosophy

Workspace deletion requires confirmation.

Workspace tokens may be reset.

Passwords remain unless explicitly changed.

---

## 33. Telegram Settings

Telegram Settings belong to the Telegram interface,

not to business logic.

---

## 34. UX Philosophy

Every workflow should follow:

Select

↓

Confirm

↓

Run

↓

Result

---

## 35. Release Quality

No TODO

No FIXME

No XXX

in release code.

---

## 36. One Responsibility per Service

Each service owns one business responsibility.

---

## 37. Stable Public APIs

Avoid unnecessary breaking changes to service interfaces.

---

## 38. Human Readable Data

Generated files should remain readable by humans.

---

## 39. No Hidden Magic

Important operations must always be:

- visible
- logged
- understandable

---

## 40. Backward Compatibility

Preserve compatibility whenever practical.

Older backups should remain readable.

---

## 41. One Canonical Model

Each concept has one canonical model.

---

## 42. Explicit Errors

Users receive friendly errors.

Technical details belong in logs.

---

## 43. Minimal Dependencies

Avoid unnecessary external libraries.

---

## 44. Performance is a Feature

Always consider scalability.

Avoid unnecessary work.

---

## 45. Design Questions

Before implementing a feature ask:

What problem does it solve?

Where does it belong?

Can an existing component solve it?

---

## 46. Production First

Every release should be tested in production before beginning the next major feature.

---

## 47. Complete Workflows

Every completed workflow must provide an explicit way back to its parent screen.

A user should never become "stuck" on a result screen.

Every workflow should naturally end with:

Result

↓

Optional Action(s)
(e.g. Download, Export)

↓

Back

↓

Parent Screen

This rule applies to every interface:

• CLI
• Telegram
• Future Web UI

Examples:

Backup
Result
→ Download
→ Back

Group Checker
Result
→ Export (future)
→ Back

Migration
Summary
→ Download Report (future)
→ Back

Reports
View
→ Export
→ Back

This rule is mandatory for all future features.

---

# Development Checklist

Before writing code ask yourself:

□ Does this fit the architecture?

□ Am I duplicating logic?

□ Can I reuse an existing service?

□ Does Telegram mirror the CLI?

□ Does this require tests?

□ Does this require logging?

□ Does this require history?

□ Does this require documentation?

□ Will this keep the project simpler?

If any answer is "No", stop and redesign before implementing.

---

# Final Principle

Architecture is a product.

Every release must strengthen it.

Never sacrifice consistency for short-term convenience.
