# Mac Manager

> Monitor your Mac's health, security and hardware from the terminal — battery alerts, live dashboard, security audit and dev-tooling inventory.

[![Lint](https://github.com/armelingu/mac-manager/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/armelingu/mac-manager/actions/workflows/lint.yml)
[![Tests](https://github.com/armelingu/mac-manager/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/armelingu/mac-manager/actions/workflows/test.yml)
[![CodeQL](https://github.com/armelingu/mac-manager/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/armelingu/mac-manager/actions/workflows/codeql.yml)
[![PyPI](https://img.shields.io/pypi/v/mac-manager.svg)](https://pypi.org/project/mac-manager/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](./CHANGELOG.md)
[![Status: alpha](https://img.shields.io/badge/status-alpha-yellow.svg)](#status)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

A Python CLI to monitor and take care of your MacBook (Apple Silicon) right from the terminal — battery, system, disk, network — with a live dashboard, automatic daily logging, and native notifications to preserve battery health.

> Designed for Apple Silicon MacBook Air/Pro. It also works on Intel, but some metrics (battery capacity, etc.) may vary.

## Installation

```bash
cd mac-manager
./install.sh
```

This will:
- create a local `venv` in `.venv/`
- install `rich` and `psutil`
- create the symlink `~/.local/bin/mm`
- register two `launchd` agents:
  - **daily log** at 09:00 → writes a snapshot to `logs/battery.csv`
  - **battery alerts** every 15 min → native macOS notification

Make sure `~/.local/bin` is in your `PATH`:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Commands

> For the **complete** reference for each command (description, options, when to use, examples), see [COMMANDS.md](./COMMANDS.md).

### Hardware and system
| Command | What it does |
|---|---|
| `mm` | General status (battery + system + disk + network) |
| `mm battery` | Charge, health, cycles, temperature, power source |
| `mm health` | CPU, RAM, memory pressure, top 5 processes |
| `mm disk` | Disk usage + local snapshots + cleanup candidates |
| `mm clean` | Lists what can be cleaned (deletes nothing) and shows the commands |
| `mm net` | Local/public IPs, SSID, Wi-Fi signal |
| `mm doctor` | 0-100 score with automatic recommendations |
| `mm watch` | Live dashboard (Ctrl+C to exit) |

### Battery — history
| Command | What it does |
|---|---|
| `mm log` | Writes a battery snapshot to the CSV |
| `mm history -n 20` | Last N recorded measurements |
| `mm alerts` | Runs the alert check (called by launchd) |

### Security
| Command | What it does |
|---|---|
| `mm security` | Audits FileVault, SIP, Firewall, Gatekeeper, pending updates, LaunchAgents, remote SSH, XProtect and provides a 0-100 score |

### Development
| Command | What it does |
|---|---|
| `mm dev` | Lists installed languages, package managers, devops, editors and CLIs — with version and path |
| `mm dev --all` | Also shows known tools that are **not** installed |
| `mm dev --check` | Lists outdated packages in Homebrew, global npm, pip and Mac App Store |

## Smart alerts

To preserve the lithium-ion battery (every cycle counts!), the agent checks every 15 min and fires a notification:

- **≥ 80% charging** → "consider unplugging" (every 2h)
- **≤ 20% on battery** → "good time to plug in" (every 30min)
- **≤ 10% on battery** → critical alert (every 10min)
- **health < 80%** → 1x per week

## History

Every day at 9 AM, a snapshot is written to `logs/battery.csv`:

```csv
timestamp,percent,is_charging,power_source,cycle_count,max_capacity_mah,design_capacity_mah,health_percent,temperature_c
2026-04-19T09:00:01,82,1,AC Power,12,4350,4380,99.3,30.5
```

In a few months you can plot the real degradation of your Mac.

## Structure

```
mac-manager/
├── mm                      # entrypoint (bash → venv python)
├── macmanager/
│   ├── cli.py              # dispatcher
│   ├── ui.py               # UI helpers
│   ├── battery.py          # ioreg + pmset
│   ├── system.py           # CPU/RAM/processes via psutil
│   ├── disk.py             # usage + snapshots + cleanup
│   ├── network.py          # Wi-Fi + IPs
│   ├── notify.py           # osascript notifications
│   ├── logger.py           # CSV history
│   ├── doctor.py           # score + tips
│   ├── alerts.py           # notification rules
│   ├── security.py         # security audit (mm security)
│   ├── dev.py              # dev tooling inventory (mm dev)
│   └── watch.py            # live dashboard
├── launchd/
│   ├── com.macmanager.battery-log.plist
│   └── com.macmanager.battery-alert.plist
├── logs/
├── install.sh
├── uninstall.sh
└── requirements.txt
```

## Uninstallation

```bash
./uninstall.sh
```

Removes launchd agents, symlink and venv. Preserves the CSVs in `logs/`.

## Status

Mac Manager is currently in **alpha**: the public CLI surface is stabilizing,
breaking changes can still happen between `0.x` releases without a deprecation
window. Once we ship `1.0.0`, every breaking change will follow
[Semantic Versioning](https://semver.org/) and a deprecation cycle.

## Changelog

All notable changes are documented in [CHANGELOG.md](./CHANGELOG.md), following
the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## Releasing

Maintainers: see [RELEASING.md](./RELEASING.md) for the full release runbook
(SemVer policy, version bump, tagging and the tag-driven GitHub Actions
pipeline that builds artifacts and cuts a GitHub Release automatically —
PyPI publication is wired with Trusted Publishing and can be activated by
flipping a single flag).

## Contributing

Contributions are very welcome — whether it's a bug report, a feature request
or a pull request. Please read the contribution guide before opening anything:

- 📖 [CONTRIBUTING.md](./CONTRIBUTING.md) — how to set up a dev environment,
  coding style, commit conventions and PR workflow.
- 🛡️ [SECURITY.md](./SECURITY.md) — how to responsibly report a vulnerability.
- 🤝 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — what we expect from everyone
  participating in this project.

> The files above are being added incrementally; until each one lands, please
> open an issue on [GitHub](https://github.com/armelingu/mac-manager/issues)
> for anything you'd like to discuss.

## License

Copyright © 2026 [Gustavo Armelin](https://github.com/armelingu).

This project is released under the [Apache License 2.0](./LICENSE) — a
permissive license that allows commercial use, modification, distribution
and private use, with patent protection. See [`NOTICE`](./NOTICE) for the
required attribution and the third-party licenses bundled at runtime.

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```
