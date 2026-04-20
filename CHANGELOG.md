# Changelog

All notable changes to **Mac Manager** are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

> **How to read this file:**
> - `Added` — new features.
> - `Changed` — changes in existing functionality.
> - `Deprecated` — soon-to-be removed features.
> - `Removed` — features removed in this release.
> - `Fixed` — bug fixes.
> - `Security` — vulnerability fixes.
>
> Unreleased changes go on top, under `[Unreleased]`. When a release is cut,
> the section is renamed to the version number with the release date.

---

## [Unreleased]

<!-- Add your changes here as you work on them. -->

---

## [0.1.0] — 2026-04-20

First public release. Mac Manager ships as a Python CLI focused on macOS
(Apple Silicon first, Intel best-effort) that monitors battery, system, disk,
network, security and the developer toolchain — all from the terminal — and
fires native notifications to help preserve battery health.

### Added

#### Core CLI (`mm`)
- `mm` (default `status`) — stacked panels with battery, system, disk and network.
- `mm battery` — full battery report: charge, state, source, health (max/design),
  charge cycles, temperature and serial number.
- `mm health` — CPU (current %, load average, cores), RAM, macOS memory pressure,
  swap, uptime and top 5 processes by CPU/memory.
- `mm disk` — `Macintosh HD` usage, local Time Machine snapshots and cleanup
  candidates (caches, Downloads, Trash, Xcode DerivedData, npm/pnpm caches).
- `mm clean` — same scan as `mm disk` plus ready-to-run shell commands; never
  deletes anything automatically.
- `mm net` — interface, local IP, public IP (via `api.ipify.org`), Wi-Fi SSID,
  channel, security, TX rate and RSSI with qualitative classification.
- `mm doctor` — overall 0–100 health score with per-check tips. Weights:
  battery health (25), cycles (15), free disk (20), memory pressure (20),
  CPU load (10), battery temperature (10).
- `mm watch` — full-screen live dashboard powered by `rich.live` with
  configurable refresh interval (`-i/--interval`).
- `mm security` — security audit with 0–100 score covering FileVault, SIP,
  Gatekeeper, Firewall, pending macOS updates, automatic update check,
  XProtect version, time since last reboot, remote SSH and LaunchAgents.
- `mm dev` — inventory of 74 known development tools across 8 categories
  (languages, version managers, package managers, devops, git, editors,
  CLI utilities, shells). Detects path and version in parallel (16 threads).
- `mm dev --all` — also lists known tools that are NOT installed.
- `mm dev --check` — outdated packages on Homebrew, global npm, pip and
  Mac App Store.
- `mm log` — appends a battery snapshot to `logs/battery.csv` (append-only).
- `mm history -n N` — prints the last N CSV entries as a table.
- `mm alerts` — evaluates the smart-alert rules once and fires native
  notifications when applicable.
- `mm --version` / `--help` and per-subcommand help via `argparse`.

#### Smart battery alerts
- High charge while charging (≥ 80%) — reminds to unplug, 2h cooldown.
- Low battery while on battery (≤ 20%) — reminds to plug in, 30 min cooldown.
- Critical battery while on battery (≤ 10%) — urgent notification, 10 min
  cooldown.
- Low battery health (< 80%) — weekly reminder.
- Per-rule cooldown state stored in `logs/.alert_state` (JSON) to prevent spam.

#### macOS integration
- Native notifications via `osascript` (`display notification ...`).
- Two `launchd` agents installed by `install.sh`:
  - `com.macmanager.battery-log` — daily snapshot at 09:00.
  - `com.macmanager.battery-alert` — alert evaluation every 15 minutes.
- Battery readout via `ioreg -rn AppleSmartBattery` and `pmset -g batt`.
- Wi-Fi readout via `system_profiler SPAirPortDataType` (no sudo required;
  `airport -I` is deprecated on Sonoma+).

#### Architecture and tooling
- Modular Python package (`macmanager/`) with one module per concern
  (`battery`, `system`, `disk`, `network`, `notify`, `logger`, `doctor`,
  `alerts`, `security`, `dev`, `watch`, `ui`, `cache`, `cli`).
- TTL in-memory cache decorator (`macmanager.cache`) used to avoid
  re-running expensive collections on every refresh of `mm watch`.
- Background warm-up of heavy collectors (`doctor`, `security`,
  `softwareupdate`) so the live dashboard never blocks the redraw.
- Daily CSV logging at `logs/battery.csv` with stable schema:
  `timestamp, percent, is_charging, power_source, cycle_count,
  max_capacity_mah, design_capacity_mah, health_percent, temperature_c`.

#### Distribution and developer experience
- `install.sh` — creates a local `.venv`, installs dependencies, builds
  the `~/.local/bin/mm` symlink, materializes the launchd plists from
  templates and loads them.
- `uninstall.sh` — removes launchd agents, symlink and venv; preserves CSV
  logs.
- `mm` shell entrypoint — portable symlink resolution (BSD `readlink`),
  always runs the package from the project root regardless of caller `cwd`.
- `requirements.txt` pinning runtime deps (`rich >= 13.7`, `psutil >= 5.9`).
- `.gitignore` covering `.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`,
  `.DS_Store` and `logs/*` (except `logs/.gitkeep`).

#### Documentation
- `README.md` — overview, installation, command summary, structure and
  uninstall.
- `COMMANDS.md` — full per-command reference with use cases, costs, options,
  examples and exit codes.
- `LICENSE` — Apache License 2.0 (full official text).
- `NOTICE` — required attribution file under Apache 2.0; lists `rich` (MIT)
  and `psutil` (BSD-3-Clause) as runtime dependencies.

[Unreleased]: https://github.com/armelingu/mac-manager/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/armelingu/mac-manager/releases/tag/v0.1.0
