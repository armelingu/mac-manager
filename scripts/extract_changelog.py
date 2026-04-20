#!/usr/bin/env python3
"""Extract the release-notes section for a given version from CHANGELOG.md.

Usage:
    python scripts/extract_changelog.py <version> [<changelog_path>]

Prints the section body (everything between the matching `## [version]` header
and the next `## [` header) to stdout. Exits non-zero if the version is not
found, so the release workflow fails loud rather than publishing an empty
release.

The format follows Keep a Changelog 1.1.0, e.g.:

    ## [0.1.0] — 2026-04-20

    ### Added
    ...

    ## [0.0.1] — 2026-04-10
"""

from __future__ import annotations

import pathlib
import re
import sys


def extract(version: str, changelog: str) -> str:
    version = version.lstrip("v")
    header_re = re.compile(
        r"^##\s*\[(?P<ver>[^\]]+)\]\s*(?:[—\-–]\s*(?P<date>\S+))?\s*$",
        re.MULTILINE,
    )
    matches = list(header_re.finditer(changelog))
    for i, m in enumerate(matches):
        if m.group("ver") == version:
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog)
            body = changelog[start:end].strip("\n")
            body = re.sub(r"\n-{3,}\s*$", "", body).rstrip()
            return body
    raise SystemExit(f"error: version {version!r} not found in CHANGELOG")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: extract_changelog.py <version> [<changelog_path>]", file=sys.stderr)
        return 2
    version = sys.argv[1]
    path = pathlib.Path(sys.argv[2]) if len(sys.argv) >= 3 else pathlib.Path("CHANGELOG.md")
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 2
    print(extract(version, path.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
