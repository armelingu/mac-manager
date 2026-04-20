# Releasing Mac Manager

This file is the maintainer runbook for cutting a new release. The pipeline
is **tag-driven**: once a tag `vX.Y.Z` is pushed, GitHub Actions takes over
and publishes the GitHub Release automatically (and, once you enable it,
the PyPI release too).

## Versioning

Mac Manager follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** — backwards-incompatible CLI / public API changes.
- **MINOR** — new features, fully backwards compatible.
- **PATCH** — bug fixes and internal improvements only.
- Pre-releases use `-rc.N`, `-beta.N`, `-alpha.N` suffixes — CI flags these
  as pre-releases automatically.

There is a **single source of truth** for the version:
`macmanager/__init__.py`. The `pyproject.toml` reads it via
`tool.hatch.version`, and the release workflow verifies that the tag you
push matches `__version__` before building anything.

## One-time setup (PyPI)

Needed only before the **first** PyPI release.

1. Create the project on PyPI (reserves the name `mac-manager`):
   - Option A — manual: upload a first wheel using a regular PyPI API token.
   - Option B — via a pending trusted publisher registration (preferred):
     https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
2. Register a **Trusted Publisher** on PyPI:
   - Owner: `armelingu`
   - Repository: `mac-manager`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. On GitHub, create an environment named `pypi`
   (Settings → Environments → New environment). Add required reviewers if
   you want manual approval before every upload.
4. In `.github/workflows/release.yml`, flip the `pypi-publish` job's
   `if: false` to `if: ${{ !contains(needs.build.outputs.version, '-') }}`
   (skips PyPI for pre-releases) and commit.

No long-lived tokens are needed — Trusted Publishing uses OIDC.

## Release checklist

### 1. Prepare the `main` branch

- [ ] All intended changes are merged to `main`.
- [ ] CI is green (Lint, Tests, CodeQL).
- [ ] `CHANGELOG.md` has an `[Unreleased]` section listing every change
      in this release, grouped by Keep-a-Changelog category
      (Added / Changed / Deprecated / Removed / Fixed / Security).

### 2. Bump the version

- [ ] Pick the next version `X.Y.Z` according to SemVer.
- [ ] Update `macmanager/__init__.py`:

  ```python
  __version__ = "X.Y.Z"
  ```

- [ ] In `CHANGELOG.md`, rename `[Unreleased]` to `[X.Y.Z] — YYYY-MM-DD`
      and open a fresh empty `[Unreleased]` section at the top.
- [ ] Update the compare links at the very bottom of `CHANGELOG.md`:

  ```md
  [Unreleased]: https://github.com/armelingu/mac-manager/compare/vX.Y.Z...HEAD
  [X.Y.Z]:      https://github.com/armelingu/mac-manager/compare/vPREV...vX.Y.Z
  ```

- [ ] Update the version badge in `README.md`:

  ```md
  [![Version](https://img.shields.io/badge/version-X.Y.Z-orange.svg)](./CHANGELOG.md)
  ```

### 3. Validate locally

```bash
# Re-run the full check locally before tagging.
source .venv/bin/activate
ruff check .
ruff format --check .
pytest
rm -rf dist/ build/
python -m build
twine check dist/*
```

All commands must succeed. `twine check` must report **PASSED** for both
the wheel and the sdist.

### 4. Commit the bump

```bash
git add macmanager/__init__.py CHANGELOG.md README.md
git commit -m "release: vX.Y.Z"
git push origin main
```

Wait for CI (Lint + Tests + CodeQL) to go green on that commit.

### 5. Tag and push

```bash
git tag -a vX.Y.Z -m "Mac Manager vX.Y.Z"
git push origin vX.Y.Z
```

Pushing the tag triggers `.github/workflows/release.yml`, which will:

1. Verify the tag matches `__version__`.
2. Build the sdist + wheel (shared artifact).
3. Extract the `[X.Y.Z]` section of `CHANGELOG.md` as release notes.
4. Create a GitHub Release `vX.Y.Z` with the wheel + sdist attached.
5. (When enabled) Publish to PyPI via Trusted Publishing.

### 6. Post-release

- [ ] Visit the new release on GitHub and skim the notes.
- [ ] `pip install mac-manager==X.Y.Z` in a clean venv and run `mm --version`
      to confirm the wheel on PyPI (once that job is enabled) is the right
      one.
- [ ] Bump the Homebrew tap (see next section).
- [ ] Announce the release (optional — Twitter/Mastodon/Bluesky).

## Updating the Homebrew tap

After every release, the formula at
[`armelingu/homebrew-tap`](https://github.com/armelingu/homebrew-tap)
needs the new `url` and `sha256`.

```bash
# 1. Compute SHA256 of the new sdist.
PYPI_URL="https://files.pythonhosted.org/packages/source/m/mac-manager/mac_manager-X.Y.Z.tar.gz"
SHA=$(curl -sL "$PYPI_URL" | shasum -a 256 | awk '{print $1}')

# 2. In the tap repo, update Formula/mac-manager.rb:
#      url    "$PYPI_URL"
#      sha256 "$SHA"
#    Also bump any `resource` blocks whose pins moved (see
#    `pip download` output to grab fresh URLs and SHAs).

# 3. Validate locally if you have brew installed:
brew audit --strict --online Formula/mac-manager.rb
brew install --build-from-source ./Formula/mac-manager.rb
brew test mac-manager

# 4. Commit and push:
git add Formula/mac-manager.rb
git commit -m "mac-manager X.Y.Z"
git push
```

The tap's CI (`brew test-bot`) will exercise the formula on macos-latest
and block the push if it fails.

## Fixing a botched release

If the release job fails mid-flight, fix the cause, delete the tag both
locally and on the remote, and repeat step 5:

```bash
git tag -d vX.Y.Z
git push --delete origin vX.Y.Z
# If a GitHub Release was created already, delete it from the web UI too.
# Now redo step 5.
```

**Never** overwrite an already-published PyPI version — bump to
`X.Y.(Z+1)` instead. PyPI is append-only.

## Pre-releases

For `vX.Y.Z-rc.N`, `vX.Y.Z-beta.N` or `vX.Y.Z-alpha.N`:

- The release workflow auto-marks them as pre-releases on GitHub.
- The PyPI publish step (once enabled) skips pre-releases by default.
  Remove the `!contains(...'-')` guard if you *want* to publish
  pre-releases to PyPI.
