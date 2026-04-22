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

### Added
- **Unit test suite (202 tests)** covering every pure function in
  the package. Focus is surgical: pure formatters, score tables,
  color pickers, dataclass contracts, and the caching layer — no
  mocks of psutil/subprocess. Suite runs in ~0.5s. Files added
  under `tests/`: `test_ui.py`, `test_doctor.py`, `test_network.py`,
  `test_battery.py`, `test_system.py`, `test_cache.py`,
  `test_security.py`, `test_alerts.py`, `test_dev.py`,
  `test_logger.py`, `test_extract_changelog.py`.
- **Coverage gate**: `[tool.coverage.report].fail_under = 28`.
  Current run lands at **32%** total, with `ui.py`, `cache.py`
  and `__init__.py` at 100%.
- **Coverage badge in README** backed by a public gist
  (`armelingu/4e1e4b488d91a1edec226428792429c7`) that the `Tests`
  workflow refreshes on every push to `main` via
  `schneegans/dynamic-badges-action`. Requires a one-time
  `GIST_SECRET` PAT — see the comment block at the top of
  `.github/workflows/test.yml`.

### Changed
- `doctor._score` signature relaxed from
  `list[tuple[float, int]]` to `Sequence[tuple[float, int]]` —
  lets callers pass literal `[(90, 25), ...]` int tuples without
  variance complaints from Mypy, and matches how the function is
  actually used inside `doctor()`.
- README installation section now treats `brew install
  armelingu/tap/mac-manager` and `pipx install mac-manager` as
  first-class paths (they both work as of v0.1.1); removes the
  "once released" disclaimers.
- Version badge in README bumped to 0.1.1.

### Fixed
- **Caching bug discovered by the new tests**: `cache.cached` and
  `cache.peek` promised to fall back to a plain function call when
  called with unhashable arguments (e.g. a `dict`), but only
  guarded against `TypeError` at tuple construction — the actual
  failure surfaced later, at `_STORE.get(key)`, and crashed the
  caller. Both paths now also run `hash(cache_key)` inside the
  `try/except` so unhashable inputs are detected eagerly and the
  fall-through path is taken as documented.
- Homebrew formula (`armelingu/homebrew-tap`) now has real SHA256
  hashes for every resource (`rich` 15.0.0, `psutil` 7.2.2,
  `pygments` 2.20.0, `markdown-it-py` 3.0.0, `mdurl` 0.1.2) and
  points `url` at the official PyPI sdist of `mac-manager` 0.1.1.
- Tap CI (`.github/workflows/test.yml` in the tap repo): replaced
  the flaky `brew test-bot --only-setup` invocation (crashed on
  the runner's pre-existing `brew doctor` warnings) with a focused
  `brew style` + `brew audit --new --online` gate on every push,
  plus a build-from-source + `brew test` job on PR/dispatch.
  `brew install --build-from-source armelingu/tap/mac-manager`
  has been verified green end-to-end on macos-latest.

---

## [0.1.1] — 2026-04-22

### Added
- **PyPI publishing via Trusted Publishing (OIDC).** The `release.yml`
  workflow now publishes to [pypi.org/project/mac-manager](https://pypi.org/project/mac-manager/)
  on every stable tag. No API tokens involved — GitHub Actions
  authenticates to PyPI via OpenID Connect using the registered
  trusted publisher (owner `armelingu`, repo `mac-manager`, workflow
  `release.yml`, environment `pypi`).
- **GitHub environment `pypi`** with deployment restricted to
  `v*.*.*` tags, so ad-hoc workflow runs from branches can't trigger
  a publish.

### Changed
- Pre-release tags (`vX.Y.Z-*`) skip PyPI publication — only stable
  tags go to the index.
- `release.yml` comment block updated to reflect the live setup.

---

## [0.1.0] — 2026-04-20

> Inaugural release. Previously this section was split between the
> end-user feature list (below) and a `[Unreleased]` block tracking
> the open-source hardening roadmap. They've been merged here so the
> tag captures the complete state shipped in v0.1.0.

### Added — Repository, packaging and tooling
- PEP 621 `pyproject.toml` with the [hatchling](https://hatch.pypa.io/) build
  backend, making Mac Manager installable via `pip install .` and publishable
  as a wheel and sdist.
- Console script entry point: `mm = macmanager.cli:main`, so `pip install`
  users get the `mm` command on their PATH.
- Optional `[dev]` extra bundling `build`, `twine`, `ruff`, `mypy`,
  `pre-commit`, `pytest` and `pytest-cov`.
- Repository metadata: improved description plus four new GitHub topics
  (`developer-tools`, `launchd`, `system-monitoring`, `command-line-tool`).

### Changed
- Minimum supported Python lowered from 3.10 to **3.9** (matches the stock
  `/usr/bin/python3` shipped with recent macOS versions).
- Package version is now read dynamically from `macmanager/__init__.py` via
  `tool.hatch.version`, keeping a single source of truth.
- `.gitignore` hardened to cover `build/`, `dist/`, `*.egg-info/`, and
  the caches produced by `pytest`, `mypy` and `ruff`.
- Code base is now lint-clean against Ruff's baseline rule set
  (`E`, `F`, `W`, `I`, `UP`, `B`, `C4`, `SIM`) and formatted with
  `ruff format` (100-col, double quotes) — configured under
  `[tool.ruff]` in `pyproject.toml`.
- GitHub Actions: **Lint** workflow running `ruff check` and
  `ruff format --check` on every push and pull request.
- GitHub Actions: **Tests** workflow running `pytest` on a matrix of
  Python 3.9 / 3.10 / 3.11 / 3.12 / 3.13 across macOS and Ubuntu, with
  coverage collected on Python 3.12 + Ubuntu and uploaded as an
  artifact.
- `tests/test_smoke.py`: initial smoke-test scaffold — asserts
  `__version__` exists and matches SemVer, every public module imports
  cleanly, and the CLI parser advertises all 13 subcommands.
- Lint and Tests status badges at the top of the README.
- GitHub Actions: **Release** workflow triggered by pushing a
  `v[0-9]+.[0-9]+.[0-9]+` tag (or manually via `workflow_dispatch`).
  It validates that `macmanager/__init__.py`'s version matches the tag,
  builds the sdist + wheel, extracts the matching CHANGELOG section as
  release notes and publishes a GitHub Release with the artifacts
  attached. A guarded PyPI publication step using Trusted Publishing
  (OIDC) is already wired — flip one `if:` to turn it on.
- `scripts/extract_changelog.py`: small helper that extracts a given
  release's notes from `CHANGELOG.md` using the Keep a Changelog
  header format.
- **Dependabot**: weekly version updates for GitHub Actions and Python
  dependencies (Monday 06:00 America/Sao_Paulo), with minor/patch
  bumps grouped into a single PR per ecosystem and major bumps routed
  to their own PR for careful review.
- **CodeQL**: Python security-and-quality analysis on every push and
  pull request targeting `main`, plus a scheduled weekly scan
  (Monday 07:00 UTC).
- **`RELEASING.md`**: maintainer runbook covering SemVer policy, the
  pre-release checklist, how to enable PyPI Trusted Publishing and how
  to recover from a botched release.
- PyPI version badge and CodeQL status badge added to the README; both
  "light up" automatically once the first release lands.
- Distribution artifacts (sdist + wheel) validated with `twine check`
  — both pass strict metadata + README rendering validation.
- **Homebrew tap** ([`armelingu/homebrew-tap`](https://github.com/armelingu/homebrew-tap))
  bootstrapped with a Python virtualenv-based formula, README and a
  `brew test-bot` CI workflow that audits and test-installs every
  formula on macOS-latest. Formula `url`/`sha256` are placeholders
  until the first release lands; activation is documented in
  [`RELEASING.md`](./RELEASING.md).
- README's "Installation" section now showcases three install paths:
  Homebrew (recommended once released), pip/pipx (once on PyPI) and
  the existing `./install.sh` source flow (works today).
- **Mypy** static type checking enabled with a pragmatic strict-ish
  config: `strict_optional`, `warn_unreachable`, `warn_redundant_casts`,
  `check_untyped_defs`, `no_implicit_reexport`. Codebase is currently
  clean — no `# type: ignore` of any kind. Per-module overrides relax
  the few legitimately dynamic spots (`@cached`, tests).
- **Type check** workflow runs mypy on Python 3.9 and 3.13 (range
  floor and ceiling) on every push and pull request.
- README gains a Type check status badge.
- **Pre-commit** (`.pre-commit-config.yaml`): 13 hooks that run on
  every commit — file hygiene (trailing whitespace, EOL fixer,
  yaml/toml/json validators, large-file guard, merge-conflict
  detector, executable/shebang sanity), Ruff lint+format and Mypy.
  Versions are pinned to match the CI workflows; install once with
  `pre-commit install`.
- **`.editorconfig`**: project-wide editor conventions — UTF-8, LF,
  4-space Python (100 cols), 2-space YAML/TOML/JSON/Markdown/Ruby/
  shell, tabs for `Makefile`. Generated trees (`dist/`, `build/`,
  `.venv/`) are explicitly excluded from formatting rules.
- `scripts/extract_changelog.py` is now properly executable, caught
  by the new `check-shebang-scripts-are-executable` pre-commit hook.
- **Community health files** (drives the GitHub Insights → Community
  Standards checklist to 100%):
  - `CONTRIBUTING.md`: full contributor guide (dev setup, commit/PR
    workflow, code style, contribution licensing).
  - `CODE_OF_CONDUCT.md`: verbatim Contributor Covenant 2.1 with
    enforcement contact.
  - `SECURITY.md`: supported-version table, two private reporting
    channels (GitHub Private Vulnerability Reporting + email),
    response-time SLOs, 90-day coordinated disclosure policy.
- **Issue templates** (`.github/ISSUE_TEMPLATE/`): structured `Bug
  report` and `Feature request` forms (YAML schema), plus a config
  that disables blank issues and routes questions to Discussions and
  vulnerabilities to private reporting.
- **Pull request template** (`.github/PULL_REQUEST_TEMPLATE.md`):
  type-of-change checklist, related-issues block, screenshots/output
  section and a contributor checklist that mirrors the
  CONTRIBUTING.md requirements.
- **Sponsor button** (`.github/FUNDING.yml`): scaffolded with every
  major channel commented out — flip them on once accounts are
  registered.
- **Branch protection** on `main`: 13 required status checks
  (Lint + Tests 5×2 matrix + Type check 2 cells), strict mode (PRs
  must be up-to-date with `main` before merge), required linear
  history, force-push and deletion blocked, conversation resolution
  enforced, signed commits encouraged. `enforce_admins=false` keeps
  the door open for emergency admin pushes.
- **Repo-wide settings**: squash-merge as the only allowed merge
  style (linear-history-friendly), auto-delete head branch after
  merge, GitHub Discussions enabled.
- **Dependabot auto-merge** workflow (`.github/workflows/dependabot-automerge.yml`):
  auto-approves and squash-merges Dependabot PRs that are pure
  patch- or minor-version bumps once every required status check
  is green; major bumps trigger a comment instead and stay manual.

### Added — End-user features

> Mac Manager ships as a Python CLI focused on macOS
> (Apple Silicon first, Intel best-effort) that monitors battery, system, disk,
> network, security and the developer toolchain — all from the terminal — and
> fires native notifications to help preserve battery health.

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

[Unreleased]: https://github.com/armelingu/mac-manager/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/armelingu/mac-manager/releases/tag/v0.1.1
[0.1.0]: https://github.com/armelingu/mac-manager/releases/tag/v0.1.0
