# Contributing to Mac Manager

First off — thanks for taking the time to contribute. Mac Manager is a small,
focused CLI and the contribution surface is intentionally simple: clear
issues, focused pull requests, green CI.

This guide is the contract between you and the maintainers. Please read it
once before opening an issue or PR.

## Table of contents

- [Code of Conduct](#code-of-conduct)
- [Ways to contribute](#ways-to-contribute)
- [Reporting bugs](#reporting-bugs)
- [Suggesting features](#suggesting-features)
- [Reporting security issues](#reporting-security-issues)
- [Development environment](#development-environment)
- [Coding style and guidelines](#coding-style-and-guidelines)
- [Commit messages](#commit-messages)
- [Pull request workflow](#pull-request-workflow)
- [Releasing (maintainers)](#releasing-maintainers)
- [License of contributions](#license-of-contributions)

## Code of Conduct

This project adheres to the [Contributor Covenant 2.1](./CODE_OF_CONDUCT.md).
By participating you agree to uphold it. Report unacceptable behaviour to
**armelingu@gmail.com**.

## Ways to contribute

- **Bug reports** — see [Reporting bugs](#reporting-bugs).
- **Feature requests** — see [Suggesting features](#suggesting-features).
- **Documentation** — typos, clarifications, missing examples, better
  diagrams: all welcome via PR.
- **Code** — bug fixes, refactors, new features, additional macOS-only
  metrics. Discuss bigger changes in an issue first.
- **Triage** — reproducing reported bugs and adding useful comments to
  open issues is genuinely valuable.

## Reporting bugs

Before opening an issue:

1. Search [existing issues](https://github.com/armelingu/mac-manager/issues?q=is%3Aissue) —
   yours might already be reported.
2. Make sure you're on the latest version (`mm --version`).
3. Try reproducing on a clean install: `pipx reinstall mac-manager` (or
   re-run `./install.sh` from a fresh clone).

Then open a [Bug report](https://github.com/armelingu/mac-manager/issues/new?template=bug_report.md)
and include:

- macOS version + chip (Apple Silicon / Intel).
- Python version (`python3 --version`).
- Mac Manager version (`mm --version`).
- The exact command you ran.
- The full output (use a code block, not a screenshot).
- What you expected versus what happened.

## Suggesting features

Open a [Feature request](https://github.com/armelingu/mac-manager/issues/new?template=feature_request.md)
and include:

- The user problem you're trying to solve.
- A sketch of the proposed CLI surface (subcommand name, flags, sample
  output).
- Why it belongs in Mac Manager (vs. a separate tool).
- macOS-only or cross-platform? (Apple Silicon-only by design today; that
  can change with explicit motivation.)

## Reporting security issues

**Do not open a public issue for vulnerabilities.** See
[SECURITY.md](./SECURITY.md) for the responsible-disclosure process.

## Development environment

You'll need:

- macOS 12+ (Apple Silicon recommended; Intel best-effort).
- Python 3.9 or newer.
- [Homebrew](https://brew.sh) (only required if you want to run
  `pre-commit autoupdate` or test the Homebrew formula).

```bash
git clone https://github.com/armelingu/mac-manager.git
cd mac-manager

# 1. Create the virtualenv and install Mac Manager + every dev tool.
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# 2. Install pre-commit hooks (runs ruff, ruff-format, mypy on every commit).
pre-commit install

# 3. Sanity check.
ruff check .
ruff format --check .
mypy
pytest
mm --version
```

If any of those fail, please open an issue — the goal is "git clone → green
in five minutes".

## Coding style and guidelines

- **Formatter:** `ruff format` (100 columns, double quotes). Don't fight it.
- **Lint:** `ruff check` must be green. Justified ignores go in the
  `ignore` list inside `pyproject.toml`, not as `# noqa` comments.
- **Types:** new code should add type hints. `mypy` must stay green.
- **Imports:** keep them sorted (`ruff` enforces isort). `macmanager` and
  `tests` are first-party; everything else is third-party.
- **Comments:** explain *why*, not *what*. The code itself describes
  *what*. Avoid narration like `# Increment counter`.
- **Docstrings:** module-level docstrings are mandatory; function
  docstrings are recommended for non-trivial behaviour.
- **No print statements** in `macmanager/` — use the project's `console`
  helper from `macmanager.ui` so output is consistent and Rich-aware.
- **No new runtime dependencies without discussion.** `rich` and `psutil`
  are deliberate choices; adding more bloats install time and
  Homebrew-formula maintenance.

## Commit messages

We follow a **light Conventional Commits** style:

```
<type>(<scope>): <imperative subject in lowercase>

<paragraph explaining the *why*; what the code does is in the diff>

<optional footer: closes #123, etc>
```

Examples:

- `feat(battery): show charge cycles when available`
- `fix(network): handle missing Wi-Fi interface on Intel Macs`
- `docs(readme): clarify how to install via Homebrew`
- `ci: pin ruff to 0.16.x in the lint workflow`
- `refactor(disk): extract snapshot parser into its own helper`

Common `type`s: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`,
`ci`, `build`, `release`.

Subjects are written in imperative mood ("add", not "added") and stay under
72 characters. The body is wrapped at 72 columns and explains the *why* —
the *what* is already in the diff.

## Pull request workflow

1. **Fork** the repo and create a focused branch:
   `git checkout -b feat/battery-cycles`. One PR = one logical change.
2. **Develop locally** with `pre-commit install` active.
3. **Update CHANGELOG.md** under the `[Unreleased]` section, in the
   correct Keep-a-Changelog category (`Added`/`Changed`/etc).
4. **Push and open the PR** against `main`. Fill in the PR template.
5. **CI must be green**: Lint, Tests (10 cells), Type check (2 cells)
   and CodeQL. Failing checks block merge automatically.
6. **At least one maintainer review** is required.
7. We **squash-merge**, so the PR title becomes the commit subject —
   make it count.

Small, well-described PRs are reviewed and merged in days. PRs that
bundle ten things take weeks. Help us help you.

## Releasing (maintainers)

See [RELEASING.md](./RELEASING.md) for the full release runbook
(SemVer policy, version bump, tagging, the tag-driven Actions pipeline,
PyPI Trusted Publishing activation and the Homebrew tap update).

## License of contributions

By submitting a contribution, you agree that:

- Your contribution is licensed under the same terms as the project
  ([Apache License 2.0](./LICENSE)).
- You have the right to license the contribution under those terms (it's
  your work, or your employer authorizes you to contribute it on their
  behalf, etc).

We don't require a separate CLA — Apache 2.0 already includes the patent
grant we need.

---

Thanks again. We appreciate your time.
