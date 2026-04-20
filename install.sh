#!/usr/bin/env bash
# Installs dependencies in a local venv, creates a symlink at ~/.local/bin/mm
# and registers the launchd agents (daily log + battery alerts).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Mac Manager · install"
echo "    directory: $SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not found. Install via App Store or: brew install python" >&2
    exit 1
fi

# 1. Create venv
if [ ! -d ".venv" ]; then
    echo "==> creating venv (.venv)"
    python3 -m venv .venv
fi

echo "==> installing dependencies"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

# 2. Make the entrypoint executable
chmod +x mm

# 3. Symlink in ~/.local/bin (created if it doesn't exist)
mkdir -p "$HOME/.local/bin"
ln -sf "$SCRIPT_DIR/mm" "$HOME/.local/bin/mm"
echo "==> symlink: $HOME/.local/bin/mm -> $SCRIPT_DIR/mm"

# 4. Ensure logs directory
mkdir -p "$SCRIPT_DIR/logs"

# 5. Install launchd agents (daily log + alerts)
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_DIR"

for name in com.macmanager.battery-log com.macmanager.battery-alert; do
    src="launchd/${name}.plist"
    dest="$LAUNCH_DIR/${name}.plist"
    sed "s|{{SCRIPT_DIR}}|$SCRIPT_DIR|g" "$src" > "$dest"
    launchctl unload "$dest" 2>/dev/null || true
    launchctl load "$dest"
    echo "==> launchd: $name loaded"
done

# 6. PATH check
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *)
        echo ""
        echo "[warning] $HOME/.local/bin is not in your PATH."
        echo "    Add it to your ~/.zshrc:"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        ;;
esac

echo ""
echo "Installed. Available commands:"
echo "   mm              # general status"
echo "   mm battery      # battery details"
echo "   mm health       # CPU, RAM, processes"
echo "   mm disk         # usage and cleanup"
echo "   mm net          # network / Wi-Fi"
echo "   mm doctor       # health score"
echo "   mm watch        # live dashboard"
echo "   mm log          # battery snapshot → CSV"
echo "   mm history -n 20 # last measurements"
echo ""
echo "Active automation:"
echo "   • Daily log at 09:00 → logs/battery.csv"
echo "   • Battery alerts every 15 min (native notifications)"
echo ""
echo "To uninstall everything: ./uninstall.sh"
