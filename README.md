# 🧠 Mute Platform

**Intelligent VPN Operations Platform**

![Version](https://img.shields.io/badge/version-0.3.0--dev-blue)
![Status](https://img.shields.io/badge/status-development-yellow)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

An intelligent business platform for managing, analyzing, and growing VPN businesses
through smart tools, analytics, and AI.

Mute Platform is **not** a PasarGuard application — it is a **Decision Intelligence
Platform**. PasarGuard is the first supported integration. Future modules are documented as
**Released**, **In Development**, or **Planned** — never as already implemented.

---

## 📌 Current Version

**0.3.0-dev — Development**

**Status:** Development  
**Next milestone:** Groups Module

Active development after the stable v0.2.1 line. Focus is the Groups domain
(Check · Modify · History) and a Shared Group Operation Engine. Migration remains deferred.

---

## 🛡️ Reliability

- JSON persistence is atomic — a failed write never corrupts an existing file.
- The workspace registry automatically recovers from corruption by scanning on-disk manifests.
- Workspace names are validated to prevent unsafe or colliding directories.
- CLI and Telegram share the same workspace logging.

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
│     │     └── Workspace Dashboard → Backup · Group Engine · Migration (deferred)
│     ├── Settings
│     └── About
│
└── Telegram (owner-only)
      Home
      ├── My Workspaces
      │     └── Workspace Dashboard → Backup · Group Engine · Migration (deferred)
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

## Deployment

Deploy the Telegram bot as a systemd service on Ubuntu/Debian. The example below assumes the
repository is installed at `/opt/MutePlatform`.

**1. Clone the repository**

```bash
sudo git clone https://github.com/01Shayan/MutePlatform.git /opt/MutePlatform
sudo chown -R $USER:$USER /opt/MutePlatform
cd /opt/MutePlatform
```

**2. Create a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install requirements**

```bash
pip install -r requirements.txt
```

Run the CLI once to complete the Setup Wizard and configure Telegram before starting the service.

**4. Copy the service file**

```bash
sudo cp deploy/systemd/mute-telegram.service /etc/systemd/system/
```

**5. Reload systemd**

```bash
sudo systemctl daemon-reload
```

**6. Enable the service**

```bash
sudo systemctl enable mute-telegram
```

**7. Start the service**

```bash
sudo systemctl start mute-telegram
```

**8. Check status**

```bash
sudo systemctl status mute-telegram
```

**9. View logs**

```bash
journalctl -u mute-telegram -f
```

**10. Restart after updates**

```bash
cd /opt/MutePlatform
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mute-telegram
```

If you install the repository elsewhere, edit `WorkingDirectory`, `PYTHONPATH`, and `ExecStart`
in `/etc/systemd/system/mute-telegram.service` before enabling the service.

---

## 🗺️ Roadmap

```
v0.1.0  Workspace Foundation · Backup                      Released
   ↓
v0.1.5  Telegram Interface · Installation Experience       Released
   ↓
v0.1.5.1  Patch Release                                    Released
   ↓
v0.1.6  Engineering Hardening                              Released
   ↓
v0.2.0  Group Checker                                      Released
   ↓
v0.2.1  Telegram Workspace Management                      Stable
   ↓
v0.3.0  Groups Module                                      In Development
   ↓
Migration                                                  Deferred
   ↓
v0.4.0  Reports                                            Planned
   ↓
v0.5.0  Analytics                                          Planned
   ↓
v0.6.0  Additional Integrations                            Planned
   ↓
v1.0.0  Stable Release                                     Planned
```

See [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [CHECKLIST.md](CHECKLIST.md),
[CHANGELOG.md](CHANGELOG.md), and [docs/PRODUCT.md](docs/PRODUCT.md).

---

## 🗂️ Project Structure

```
MutePlatform/
├── VERSION
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── CHECKLIST.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── .env.example
├── docs/
│   └── PRODUCT.md
├── deploy/
│   └── systemd/
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
