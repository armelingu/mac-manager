"""Alert logic: called periodically by launchd.

Rules:
- Charging and >= 80%: reminder to unplug (keeps the battery healthy)
- Not charging and <= 20%: reminder to plug in
- Not charging and <= 10%: critical alert
- Health < 80%: once per week

O estado da última notificação fica em .alert_state no diretório de dados
do usuário (Application Support), para o cooldown sobreviver a upgrades.
"""

from __future__ import annotations

import json
import time

from macmanager.battery import get_battery
from macmanager.logger import ALERT_STATE, ensure_logs
from macmanager.notify import notify

HIGH = 80
LOW = 20
CRITICAL = 10
HEALTH_WARN = 80

COOLDOWNS = {
    "high": 60 * 60 * 2,  # 2h between "unplug" reminders
    "low": 60 * 30,  # 30min between "plug in" reminders
    "critical": 60 * 10,  # 10min in critical mode
    "health": 60 * 60 * 24 * 7,  # 1x per week
}


def _load_state() -> dict:
    ensure_logs()
    if not ALERT_STATE.exists():
        return {}
    try:
        return json.loads(ALERT_STATE.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    ensure_logs()
    ALERT_STATE.write_text(json.dumps(state, indent=2))


def _can_fire(state: dict, key: str, cooldown: int) -> bool:
    last = state.get(key, 0)
    return (time.time() - last) > cooldown


def check_and_alert() -> list[str]:
    """Avalia a bateria e dispara notificações. Devolve as chaves disparadas.

    Sem bateria real (desktop / ioreg vazio) não notifica — percent=0
    nesses casos dispararia CRITICAL falso a cada 15 min via launchd.
    """
    bat = get_battery()
    if not bat.is_present():
        return []

    state = _load_state()
    fired: list[str] = []

    if bat.is_charging and bat.percent >= HIGH and _can_fire(state, "high", COOLDOWNS["high"]):
        notify(
            f"Battery at {bat.percent:.0f}%. Consider unplugging to preserve long-term health.",
            title="Time to unplug",
            sound="Glass",
        )
        state["high"] = time.time()
        fired.append("high")

    if not bat.is_charging:
        if bat.percent <= CRITICAL and _can_fire(state, "critical", COOLDOWNS["critical"]):
            notify(
                f"Battery CRITICAL at {bat.percent:.0f}%! Plug in the charger now.",
                title="Critical battery",
                sound="Sosumi",
            )
            state["critical"] = time.time()
            fired.append("critical")
        elif bat.percent <= LOW and _can_fire(state, "low", COOLDOWNS["low"]):
            notify(
                f"Battery at {bat.percent:.0f}%. Good time to plug in.",
                title="Low battery",
                sound="Submarine",
            )
            state["low"] = time.time()
            fired.append("low")

    if (
        bat.health_percent
        and bat.health_percent < HEALTH_WARN
        and _can_fire(state, "health", COOLDOWNS["health"])
    ):
        notify(
            f"Battery health at {bat.health_percent:.0f}%. "
            f"Cycles: {bat.cycle_count}. Consider servicing it.",
            title="Attention: battery health",
            sound="Funk",
        )
        state["health"] = time.time()
        fired.append("health")

    _save_state(state)
    return fired


def cmd_alerts(args=None) -> None:
    fired = check_and_alert()
    if fired:
        print("Alerts fired:", ", ".join(fired))
    else:
        print("Nothing to notify.")
