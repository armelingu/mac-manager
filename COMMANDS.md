# Mac Manager — Command Reference

Complete reference for every `mm` command. For quick help in the terminal:

```bash
mm --help              # list every command
mm <command> --help    # help for a specific command
mm --version           # installed version
```

> When you run `mm` with no arguments, it's equivalent to `mm status`: it shows a general summary of battery + system + disk + network in a single print.

---

## Summary

| Category | Command |
|---|---|
| **Hardware/system** | [`mm`](#mm-status), [`mm battery`](#mm-battery), [`mm health`](#mm-health), [`mm disk`](#mm-disk), [`mm clean`](#mm-clean), [`mm net`](#mm-net) |
| **Visualization** | [`mm watch`](#mm-watch), [`mm doctor`](#mm-doctor) |
| **Battery — history** | [`mm log`](#mm-log), [`mm history`](#mm-history), [`mm alerts`](#mm-alerts) |
| **Security** | [`mm security`](#mm-security) |
| **Development** | [`mm dev`](#mm-dev), [`mm dev --all`](#mm-dev---all), [`mm dev --check`](#mm-dev---check) |

---

## Hardware and system

### `mm` (status)
**What it does:** quick snapshot of everything — battery + system + disk + network — in stacked panels.

**When to use:** daily routine, as a first check when you open the terminal.

**Cost:** ~1s. Reads everything locally, without hitting the internet.

```bash
mm
```

---

### `mm battery`
**What it does:** complete battery report.

**Shows:**
- Current charge (%) and state (charging / full / discharging)
- Power source (AC Power / Battery Power)
- Health (max capacity / design capacity, in %)
- Real capacity in mAh
- Charge cycles (Apple considers ~1000 as battery lifespan)
- Battery temperature in °C
- Serial number

**When to use:** whenever you want fine-grained details about the battery.

```bash
mm battery
```

---

### `mm health`
**What it does:** live state of the operating system.

**Shows:**
- CPU (current % + load average for 1/5/15 min + number of cores)
- RAM (% used + GB used/total)
- macOS memory pressure (Normal/Warn/Critical) — a more relevant metric than RAM % on Apple Silicon
- Swap (if in use)
- Uptime
- Top 5 processes by CPU/memory

**When to use:** when the Mac is slow or to see what's consuming resources.

```bash
mm health
```

---

### `mm disk`
**What it does:** main disk usage + cleanup suggestions.

**Shows:**
- Total/used/free space on `Macintosh HD` (in GB and %)
- How many local Time Machine snapshots exist (usually a silent space sink)
- "Cleanup candidates" — folders like `~/Downloads`, `~/Library/Caches`, `~/.Trash`, Xcode/VS Code/npm/pnpm caches — with how much each one occupies

**When to use:** when the disk is full or periodically for hygiene.

```bash
mm disk
```

---

### `mm clean`
**What it does:** shows the same cleanup candidates as `mm disk`, but adds the **ready-to-run commands** (deletes nothing automatically).

**When to use:** when you actually want to clean — copy the command and run it.

> Behavior by design: nothing is deleted without your decision. Always review before running `rm -rf` on any cache.

```bash
mm clean
```

---

### `mm net`
**What it does:** network info.

**Shows:**
- Active interface (`en0`, etc.)
- Local IP
- Public IP (queries `api.ipify.org`)
- SSID of connected Wi-Fi
- Security (WPA2/WPA3)
- Channel and width (e.g. 52 / 5GHz / 80MHz)
- TX rate in Mbps
- RSSI signal in dBm with qualitative classification (Excellent / Good / Fair / Weak)

**When to use:** Wi-Fi debugging, quickly checking IP, verifying connection quality.

```bash
mm net
```

---

## Visualization and general diagnostics

### `mm watch`
**What it does:** **full-screen live dashboard** with 4 panels (battery, system, disk, network) refreshing in real time.

**Shows:** the same data as `mm`, but auto-refreshing.

**When to use:** continuous monitoring (second screen, during meetings, etc).

**How to exit:** `Ctrl+C`.

```bash
mm watch              # default refresh every 2s
mm watch -i 5         # refresh every 5s
mm watch --interval 10
```

> Full-screen works best in Terminal.app, iTerm2, Warp or Ghostty. In the embedded terminal in Cursor it may break visually.

---

### `mm doctor`
**What it does:** computes a **0–100 score** of overall Mac health with recommendations for each item.

**Evaluates (with weights):**
- Battery health (weight 25)
- Charge cycles (weight 15)
- Free disk space (weight 20)
- Memory pressure (weight 20)
- Current CPU load (weight 10)
- Battery temperature (weight 10)

Each item gets a color (green/yellow/red) and a textual hint on how to improve.

**When to use:** weekly, or after any issue, to get an instant overall view.

```bash
mm doctor
```

---

## Battery — history and alerts

### `mm log`
**What it does:** writes **one snapshot** of the battery to `logs/battery.csv` (append-only CSV format).

**Columns:** `timestamp, percent, is_charging, power_source, cycle_count, max_capacity_mah, design_capacity_mah, health_percent, temperature_c`

**When to use:** manually almost never — `launchd` calls this automatically every day at 09:00. You can run it manually if you want an extra measurement.

```bash
mm log
```

---

### `mm history`
**What it does:** shows the last N entries of `battery.csv` in a table.

**When to use:** look at recent history, see the evolution of health/cycles.

```bash
mm history             # last 10 entries (default)
mm history -n 30       # last 30
mm history -n 200      # last 200
```

---

### `mm alerts`
**What it does:** runs the **smart alert logic** once. Checks the current battery state and fires a native macOS notification if any rule is triggered.

**Current rules (with cooldown to avoid spam):**
| Condition | Notification | Cooldown |
|---|---|---|
| Charging + ≥80% | "Time to unplug" — preserves battery long-term | 2h |
| On battery + ≤20% | "Battery low, good time to plug in" | 30 min |
| On battery + ≤10% | "Battery CRITICAL" | 10 min |
| Health < 80% | "Attention: battery health" | 1× per week |

**When to use:** manually almost never — `launchd` calls this every 15 min. Useful for testing if notifications are working.

```bash
mm alerts
```

> The state of the last notification is kept in `logs/.alert_state` (JSON with timestamps), preventing spam.

---

## Security

### `mm security`
**What it does:** complete macOS security audit with a **0–100 score**.

**Checks (with weights):**
| Check | Weight | What it validates |
|---|---|---|
| macOS version | info | which macOS you're running |
| FileVault | 3 | is disk encryption enabled? |
| SIP | 3 | is System Integrity Protection active? |
| Gatekeeper | 2 | blocks unsigned apps? |
| Firewall | 2 | macOS firewall active? |
| Pending updates | 2 | how many macOS updates are missing |
| Automatic check | 1 | does macOS look for updates by itself? |
| XProtect | info | version of the built-in antimalware |
| Time since last reboot | 1 | < 7d = OK, < 21d = WARN, > 21d = FAIL |
| Remote SSH | 1 | is port 22 open? (only enable if you use it) |
| LaunchAgents (login) | 1 | how many agents load on your login |

Each item returns `OK` / `WARN` / `FAIL` / `INFO` and, when applicable, a tip on how to fix it.

**When to use:** after buying a new Mac, after reinstalling macOS, or periodically (1× per month).

```bash
mm security
```

---

## Development

### `mm dev`
**What it does:** inventory of the **development tools installed** on your Mac.

**Categories checked (74 tools in total):**
| Category | Examples |
|---|---|
| Languages | Python, Node, Deno, Bun, Ruby, Go, Rust, Java, Swift, PHP, Elixir, Erlang, Lua, Perl, Zig, Kotlin |
| Version managers | nvm, fnm, volta, pyenv, rbenv, asdf, mise |
| Package managers | Homebrew, npm, pnpm, yarn, pip, pipx, poetry, uv, cargo, gem, composer, mas |
| DevOps / Infra | Docker, Podman, Colima, kubectl, Helm, Terraform, Pulumi, Ansible, AWS/gcloud/Azure CLI, Vercel, Netlify, Fly.io |
| Git & GitHub | git, gh, git-lfs, pre-commit |
| Editors / IDEs | VS Code, Cursor, Sublime, Neovim, Vim, Emacs, Xcode CLT |
| CLI utilities | tmux, jq, ripgrep, fzf, bat, eza, fd, htop, btop, zoxide, starship |
| Shells | zsh, bash, fish |

By default it shows **only what's installed**, with version and path. Collected in parallel (16 threads) → takes ~2-4s.

**When to use:** environment audit, debug "which version of X do I have?", documenting setup for someone else.

```bash
mm dev
```

---

### `mm dev --all`
**What it does:** same as `mm dev`, but also shows **known tools that are NOT installed** (in gray, marked as "not installed").

**When to use:** discover what's missing in your stack, plan installations.

```bash
mm dev --all
```

---

### `mm dev --check`
**What it does:** queries **outdated packages** in every ecosystem that offers that info for free.

**Checks:**
| Source | Internal command | How to update |
|---|---|---|
| Homebrew | `brew outdated --quiet` | `brew upgrade` |
| npm global | `npm outdated -g --parseable` | `npm update -g` |
| pip | `pip3 list --outdated` | `pip3 install -U <package>` |
| Mac App Store | `mas outdated` | `mas upgrade` |

**When to use:** weekly maintenance routine. If something shows many outdated packages, it's worth upgrading.

```bash
mm dev --check
```

> Can take 10–30s depending on the number of packages (especially `npm outdated -g` is slow).

---

## Commands invoked by launchd (background)

You normally **don't** run these manually — they stay active automatically after `install.sh`:

| When it runs | Command | What it does |
|---|---|---|
| Daily at 09:00 | `mm log` | Writes a battery snapshot to the CSV |
| Every 15 minutes | `mm alerts` | Checks rules and fires notifications if needed |

To confirm they're active:
```bash
launchctl list | grep macmanager
```

To stop/restart manually:
```bash
launchctl unload ~/Library/LaunchAgents/com.macmanager.battery-log.plist
launchctl load   ~/Library/LaunchAgents/com.macmanager.battery-log.plist
```

---

## Useful combinations

```bash
# Quick daily routine
mm

# Complete diagnostics (~30s)
mm doctor && mm security

# Monthly audit (install updates, check health)
mm dev --check
mm security
mm clean

# Live monitoring
mm watch

# See battery evolution
mm history -n 30
```

---

## Output and exit codes

- All commands exit with `0` on success.
- `mm alerts` always exits with `0` (even when it fires a critical alert — it's just a notification).
- Commands that fail to collect a metric (e.g. sandbox blocking) return `WARN`/`?` instead of erroring out.

## Where the data lives

| File | What it has |
|---|---|
| `logs/battery.csv` | Append-only history of battery measurements |
| `logs/.alert_state` | Timestamps of the last notification of each type (JSON, controls cooldown) |
| `logs/launchd-log.{out,err}` | stdout/stderr of the agent that runs `mm log` |
| `logs/launchd-alert.{out,err}` | stdout/stderr of the agent that runs `mm alerts` |

## Reinstall / uninstall

```bash
./install.sh    # creates venv, symlink ~/.local/bin/mm and loads launchd agents
./uninstall.sh  # removes everything (preserves CSVs in logs/)
```
