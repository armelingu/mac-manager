"""Tests for `scripts/extract_changelog.py`.

The script parses CHANGELOG.md and feeds the extracted body into the
release workflow's GitHub Release notes. A bug here is immediately
visible to every user — it ships straight to the release page on every
tag push. So we keep the test matrix tight but exhaustive for the
tricky cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can `import extract_changelog`.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import extract_changelog  # noqa: E402 (deliberately imported after sys.path insertion)

SIMPLE_CHANGELOG = """\
# Changelog

## [0.2.0] — 2026-05-01

### Added
- New dashboard layout.

## [0.1.0] — 2026-04-20

### Added
- Initial release.

### Fixed
- Nothing to fix yet.
"""


class TestExtractBasic:
    def test_pulls_out_first_version(self) -> None:
        body = extract_changelog.extract("0.2.0", SIMPLE_CHANGELOG)
        assert "### Added" in body
        assert "New dashboard layout." in body
        # Must not include the next section's header.
        assert "0.1.0" not in body
        assert "Initial release." not in body

    def test_pulls_out_last_version(self) -> None:
        body = extract_changelog.extract("0.1.0", SIMPLE_CHANGELOG)
        assert "### Added" in body
        assert "Initial release." in body
        # Must not include the previous section's content.
        assert "New dashboard layout." not in body

    def test_version_prefix_v_is_stripped(self) -> None:
        a = extract_changelog.extract("0.1.0", SIMPLE_CHANGELOG)
        b = extract_changelog.extract("v0.1.0", SIMPLE_CHANGELOG)
        assert a == b

    def test_missing_version_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            extract_changelog.extract("9.9.9", SIMPLE_CHANGELOG)


class TestFooterHandling:
    """Regression for the bug where the last version's body included the
    markdown link-reference footer (`[Unreleased]: https://...`)."""

    def test_link_references_are_not_part_of_the_last_section(self) -> None:
        changelog = """\
## [0.1.0] — 2026-04-20

### Added
- First release.

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0
"""
        body = extract_changelog.extract("0.1.0", changelog)
        assert "First release." in body
        assert "[Unreleased]" not in body
        assert "example.com" not in body

    def test_multiple_trailing_references_are_all_excluded(self) -> None:
        changelog = """\
## [0.3.0] — 2026-06-01

### Changed
- Interesting change.

[Unreleased]: https://e.com/compare/v0.3.0...HEAD
[0.3.0]: https://e.com/releases/tag/v0.3.0
[0.2.0]: https://e.com/releases/tag/v0.2.0
[0.1.0]: https://e.com/releases/tag/v0.1.0
"""
        body = extract_changelog.extract("0.3.0", changelog)
        assert "Interesting change." in body
        assert "https://" not in body


class TestHeaderFormatting:
    """The regex tolerates several Keep a Changelog header variations:
    em-dash, en-dash, or a plain hyphen between version and date; the
    date itself is optional."""

    @pytest.mark.parametrize(
        "header",
        [
            "## [0.1.0] — 2026-04-20",  # em-dash
            "## [0.1.0] - 2026-04-20",  # hyphen
            "## [0.1.0] – 2026-04-20",  # en-dash
            "## [0.1.0]",  # no date
            "## [0.1.0]  ",  # trailing spaces
        ],
    )
    def test_accepts_multiple_header_styles(self, header: str) -> None:
        changelog = f"{header}\n\n### Added\n- A thing.\n"
        body = extract_changelog.extract("0.1.0", changelog)
        assert "A thing." in body


class TestBodyTrimming:
    def test_strips_leading_and_trailing_newlines(self) -> None:
        changelog = SIMPLE_CHANGELOG
        body = extract_changelog.extract("0.2.0", changelog)
        assert not body.startswith("\n")
        assert not body.endswith("\n")

    def test_preserves_internal_blank_lines(self) -> None:
        # Markdown relies on blank lines between sections, so the
        # extractor should keep them in the middle of the body.
        changelog = """\
## [1.0.0] — 2026-01-01

### Added
- Foo

### Fixed
- Bar
"""
        body = extract_changelog.extract("1.0.0", changelog)
        assert "### Added" in body
        assert "### Fixed" in body
        # A blank line must separate the two subsections.
        added_idx = body.index("### Added")
        fixed_idx = body.index("### Fixed")
        between = body[added_idx:fixed_idx]
        assert "\n\n" in between


class TestRealChangelog:
    """Smoke test against the repository's own CHANGELOG.md. If the
    actual release notes for the current `__version__` can't be
    extracted, the release workflow would silently publish an empty
    body."""

    def test_current_version_is_present(self) -> None:
        import macmanager

        path = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
        if not path.is_file():
            pytest.skip("CHANGELOG.md not found in working tree")

        body = extract_changelog.extract(
            macmanager.__version__,
            path.read_text(encoding="utf-8"),
        )
        assert body.strip(), "extracted body for current version is empty"
        # Link references must not leak into release notes.
        assert "[Unreleased]:" not in body
        assert f"[{macmanager.__version__}]:" not in body
