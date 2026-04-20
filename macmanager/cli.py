"""Main CLI: subcommand dispatcher."""

from __future__ import annotations

import argparse
import sys

from macmanager import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mm",
        description="Mac Manager — monitor and take care of your MacBook from the terminal.",
    )
    p.add_argument("--version", action="version", version=f"mac-manager {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("battery", help="Complete battery report")
    sub.add_parser("health",  help="CPU, memory, processes and uptime")
    sub.add_parser("disk",    help="Disk usage and cleanup candidates")
    sub.add_parser("clean",   help="Cleanup suggestions (deletes nothing)")
    sub.add_parser("net",     help="Network and Wi-Fi information")
    sub.add_parser("doctor",  help="Overall health score + recommendations")
    sub.add_parser("log",     help="Records a battery snapshot to the CSV")

    history = sub.add_parser("history", help="Shows the last N measurements")
    history.add_argument("-n", type=int, default=10, help="how many lines to show (default 10)")

    watch = sub.add_parser("watch", help="Live dashboard (Ctrl+C to exit)")
    watch.add_argument("-i", "--interval", type=int, default=2, help="refresh interval in seconds")

    sub.add_parser("alerts",  help="Evaluates and fires alerts (called by launchd)")
    sub.add_parser("status",  help="Quick summary (battery + system + disk)")
    sub.add_parser("security", help="Security audit (FileVault, SIP, Firewall, ...)")

    dev = sub.add_parser("dev", help="Inventory of development tools")
    dev.add_argument("--all", action="store_true",
                     help="also show known tools that are not installed")
    dev.add_argument("--check", action="store_true",
                     help="list outdated packages (brew, npm -g, pip, mas)")

    return p


def cmd_status(args=None) -> None:
    from macmanager.battery import render_battery_panel
    from macmanager.disk import render_disk_panel
    from macmanager.network import render_network_panel
    from macmanager.system import render_system_panel
    from macmanager.ui import console
    console.print(render_battery_panel())
    console.print(render_system_panel())
    console.print(render_disk_panel(full=False))
    console.print(render_network_panel())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        cmd_status(args)
        return 0

    if args.command == "dev" and getattr(args, "check", False):
        from macmanager.dev import cmd_dev_check
        cmd_dev_check(args)
        return 0

    handlers = {
        "battery":  "macmanager.battery:cmd_battery",
        "health":   "macmanager.system:cmd_health",
        "disk":     "macmanager.disk:cmd_disk",
        "clean":    "macmanager.disk:cmd_clean",
        "net":      "macmanager.network:cmd_net",
        "doctor":   "macmanager.doctor:cmd_doctor",
        "log":      "macmanager.logger:cmd_log",
        "history":  "macmanager.logger:cmd_history",
        "watch":    "macmanager.watch:cmd_watch",
        "alerts":   "macmanager.alerts:cmd_alerts",
        "security": "macmanager.security:cmd_security",
        "dev":      "macmanager.dev:cmd_dev",
        "status":   None,
    }

    handler = handlers.get(args.command)
    if handler is None:
        cmd_status(args)
        return 0

    module_path, fn_name = handler.split(":")
    module = __import__(module_path, fromlist=[fn_name])
    getattr(module, fn_name)(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
