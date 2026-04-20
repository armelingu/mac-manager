#!/usr/bin/env bash
# Removes launchd agents, symlink and venv. Does not delete the CSV logs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

echo "==> Mac Manager · uninstall"

for name in com.macmanager.battery-log com.macmanager.battery-alert; do
    plist="$LAUNCH_DIR/${name}.plist"
    if [ -f "$plist" ]; then
        launchctl unload "$plist" 2>/dev/null || true
        rm -f "$plist"
        echo "==> launchd removed: $name"
    fi
done

if [ -L "$HOME/.local/bin/mm" ]; then
    rm "$HOME/.local/bin/mm"
    echo "==> symlink removed"
fi

if [ -d "$SCRIPT_DIR/.venv" ]; then
    rm -rf "$SCRIPT_DIR/.venv"
    echo "==> venv removed"
fi

echo ""
echo "Uninstalled. The logs in logs/ were preserved."
