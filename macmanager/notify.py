"""Native macOS notifications via osascript."""

from __future__ import annotations

import shlex
import subprocess


def notify(
    message: str, title: str = "Mac Manager", subtitle: str = "", sound: str = "Glass"
) -> None:
    """Fires a native macOS notification."""
    parts = [f"display notification {shlex.quote(message)} with title {shlex.quote(title)}"]
    if subtitle:
        parts.append(f"subtitle {shlex.quote(subtitle)}")
    if sound:
        parts.append(f"sound name {shlex.quote(sound)}")
    script = " ".join(parts)
    subprocess.run(["osascript", "-e", script], check=False)
