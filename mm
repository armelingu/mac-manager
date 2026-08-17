#!/usr/bin/env bash
# Mac Manager entrypoint. Runs the Python package inside the local venv.
# Works when called by absolute path, relative path, or via symlink.
set -e

# Resolve symlinks portably (BSD/macOS doesn't support `readlink -f`).
SOURCE="${BASH_SOURCE[0]:-$0}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

VENV_PY="$SCRIPT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo "Mac Manager: venv not found at $SCRIPT_DIR/.venv" >&2
    echo "Run: $SCRIPT_DIR/install.sh" >&2
    exit 1
fi

# Absolute wrapper path for `mm setup` — launchd must exec this file,
# not `python -m` (argv0 is cli.py when we use -m).
export MACMANAGER_BIN="$SCRIPT_DIR/mm"

# Run from the project root to ensure the package is discovered,
# regardless of the caller's cwd (terminal or launchd).
cd "$SCRIPT_DIR"
exec "$VENV_PY" -m macmanager.cli "$@"
