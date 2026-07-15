# 🧠 Mute Platform

**Intelligent VPN Operations Platform**

![Version](https://img.shields.io/badge/version-v0.1.5-blue)
![Status](https://img.shields.io/badge/status-stable-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

An intelligent business platform for managing, analyzing, and growing VPN businesses
through smart tools, analytics, and AI.

Mute Platform is **not** a PasarGuard application — it is a **Decision Intelligence
Platform**. PasarGuard is the first supported integration. Future modules are documented as
**Released**, **In Development**, or **Planned** — never as already implemented.

---

## 📌 Current Version

**v0.1.5 — Released**

Builds the Telegram interface and the installation experience on top of the frozen v0.1.0
Workspace Foundation and Backup module. The core architecture, backup logic, and service layer
are unchanged.

---

## ✅ Current Features

- ✔ Workspace Management
- ✔ PasarGuard Integration
- ✔ Secure Authentication
- ✔ Backup Module
- ✔ Backup History · Delete Backup · Delete All Backups
- ✔ Per Workspace Storage · Per Workspace Logging
- ✔ Modern CLI Interface
- ✔ **Telegram Interface** (owner-only bot)
- ✔ **Telegram Backup Interface** (create export, history, delete, download)
- ✔ **First-Run Setup Wizard**
- ✔ **Automatic Configuration Migration**

---

## 🖥️ Supported Interfaces

| Interface | Description |
|-----------|-------------|
| **CLI** | Full interactive terminal application |
| **Telegram** | Owner-only bot mirroring the Backup workflow (polling) |

Both interfaces share the same application services — no business logic is duplicated.

---

## 🤖 Telegram Interface

- **Owner-only.** Only the Telegram user IDs listed in `telegram.owner_ids` may interact with
  the bot. Everyone else is silently ignored.
- **Polling only.** No webhook, reverse proxy, domain, or SSL is required — ideal for a plain
  Linux VPS.
- **Backup workflow.** Mirrors the CLI: view status, create an export (with live progress
  updates on a single edited message), browse history, delete a single backup, delete all
  backups, and download the generated archive.
- **Pure interface.** The bot calls only the application services; it never touches the
  filesystem or the panel directly.

Start the CLI first to run the Setup Wizard, then launch the bot:

```bash
PYTHONPATH=src python -m mute.interfaces.telegram.app
```

---

## 🧭 Current Architecture

```
Interfaces
│
├── CLI
│     Home
│     ├── My Workspaces
│     │     └── Workspace Dashboard → Backup · Group Checker · Migration
│     ├── Settings
│     └── About
│
└── Telegram (owner-only)
      Home
      ├── My Workspaces
      │     └── Workspace Dashboard → Backup
      │            ├── Create Export
      │            ├── Backup History
      │            └── Delete Backup → Single · All
      ├── Settings
      └── About

        │
        ▼
Application Services  (Workspace · Backup)
        │
        ▼
Integrations  (PasarGuard)
```

A *workspace* is one complete working environment: an integration, its connection settings, and
all of its own data. Modules always operate on a workspace, through the service layer.

---

## 📁 Workspace Structure

```
workspaces/
    WorkspaceName/
        workspace.json
        README.md
        backups/
        migrations/
        reports/
        exports/
        logs/
        cache/
        history/
```

---

## 🔐 Configuration

Configuration is split so that **secrets are never stored in JSON**:

```
.env                    # secrets only  → BOT_TOKEN
config/settings.json    # non-secret    → config_version, telegram.enabled, telegram.owner_ids
config/workspaces.json  # workspace registry
```

Example `config/settings.json`:

```json
{
  "config_version": 2,
  "telegram": {
    "enabled": true,
    "owner_ids": [123456789]
  }
}
```

### Automatic Configuration Migration

The schema is versioned by a top-level `config_version`. On every startup the application
upgrades an older configuration automatically — moving values into the current layout and
dropping obsolete keys. **You never need to edit configuration files by hand.** After a future
update, all you need is:

```bash
git pull
```

---

## 🔌 Supported Integrations

| Integration | Status |
|-------------|--------|
| PasarGuard | Supported |
| Marzban | Planned |
| Hiddify | Planned |
| Marzneshin | Planned |

---

## 🧰 Installation

Requires **Python 3.9+**. The target environment is a **Linux VPS**.

```bash
git clone https://github.com/01Shayan/MutePlatform.git
cd MutePlatform

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

That is the entire installation. No configuration files need to be created manually.

---

## ▶️ Running & First-Run Setup

Start the application:

```bash
PYTHONPATH=src python -m mute
```

**When the installation is not yet fully configured**, the **Setup Wizard** launches
automatically and asks three questions:

1. **Telegram Bot Token** → saved to `.env` (`BOT_TOKEN`)
2. **Telegram Owner ID** → saved to `config/settings.json` (`telegram.owner_ids`)
3. **Enable Telegram?** → saved to `config/settings.json` (`telegram.enabled`)

An installation is considered complete only when `config/settings.json` and `.env` both exist,
`BOT_TOKEN` is set, and at least one Telegram owner ID is configured. Until then — including a
fresh clone or a partial setup — the wizard runs first so you never have to edit configuration
files by hand. Once everything is in place, the wizard is skipped and the app starts directly.

To run the Telegram bot (polling), launch:

```bash
PYTHONPATH=src python -m mute.interfaces.telegram.app
```

### Updating

```bash
git pull
```

Configuration migrates automatically — no manual edits required.

---

## 🗺️ Roadmap

```
v0.1.0  Workspace Foundation · Backup                      Released
   ↓
v0.1.5  Telegram Interface · Installation Experience       Released
   ↓
v0.2.0  Group Checker                                      In Development
   ↓
v0.3.0  Migration                                          Planned
   ↓
v0.4.0  Reports                                            Planned
   ↓
v0.5.0  Analytics                                          Planned
   ↓
v0.6.0  Additional Integrations                            Planned
   ↓
v1.0.0  Stable Release                                     Planned
```

See [ROADMAP.md](ROADMAP.md), [CHECKLIST.md](CHECKLIST.md), and [CHANGELOG.md](CHANGELOG.md).

---

## 🗂️ Project Structure

```
MutePlatform/
├── README.md
├── ROADMAP.md
├── CHECKLIST.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── .env.example
├── config/
├── workspaces/          # git-ignored
├── src/mute/
└── tests/
```

---

## ✨ Project Vision

Mute Platform remains a **Decision Intelligence Platform**. The current versions focus on
building a strong foundation and interfaces. Future versions will gradually introduce Reports,
Analytics, Automation, AI-assisted recommendations, and Decision Intelligence — each released
incrementally when ready.

---

## 📄 License

[MIT](LICENSE)
