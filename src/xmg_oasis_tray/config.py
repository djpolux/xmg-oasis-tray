"""User configuration stored in %APPDATA%\\xmg-oasis-tray\\config.json."""
import copy
import json
import os
import time
from pathlib import Path

from . import protocol as P

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "xmg-oasis-tray"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "oasis_tray.log"

DEFAULTS = {
    "version": 2,
    "language": "fr",
    "follow": True,                 # apply the per-mode cooler setting on mode change
    "notify": True,                 # balloon notification on mode change
    "reapply_on_reconnect": True,   # re-apply when the cooler reconnects (Bluetooth)
    "watch_mode_file": True,        # also poll the service's mode file (fallback)
    "watch_interval_s": 3,
    "restore_on_exit": False,       # put back the cooler state found at start-up
    "broker": {"host": P.BROKER_HOST, "port": P.BROKER_PORT, "plugin_slot": 7},
    "modes": {
        P.MODE_OFFICE: {"enabled": True, "fan": "0", "pump": "default", "boost": False},
        P.MODE_GAMING: {"enabled": True, "fan": "2", "pump": "default", "boost": False},
        P.MODE_TURBO: {"enabled": True, "fan": "3", "pump": "default", "boost": False},
        P.MODE_CUSTOM: {"enabled": True, "fan": "3", "pump": "default", "boost": True},
    },
}


def log(msg: str) -> None:
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def _merge(user: dict) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    for key in ("language", "follow", "notify", "reapply_on_reconnect",
                "watch_mode_file", "restore_on_exit"):
        if key in user:
            cfg[key] = user[key] if key == "language" else bool(user[key])
    if cfg["language"] not in ("fr", "en"):
        cfg["language"] = "en"
    try:
        cfg["watch_interval_s"] = max(1, min(60, int(user.get("watch_interval_s", cfg["watch_interval_s"]))))
    except (TypeError, ValueError):
        pass
    b = user.get("broker") or {}
    try:
        cfg["broker"]["host"] = str(b.get("host", cfg["broker"]["host"]))
        cfg["broker"]["port"] = int(b.get("port", cfg["broker"]["port"]))
        slot = int(b.get("plugin_slot", cfg["broker"]["plugin_slot"]))
        cfg["broker"]["plugin_slot"] = slot if slot in P.PLUGIN_SLOTS else 7
    except (TypeError, ValueError):
        pass
    for mode, m in (user.get("modes") or {}).items():
        if mode not in cfg["modes"] or not isinstance(m, dict):
            continue
        target = cfg["modes"][mode]
        target["enabled"] = bool(m.get("enabled", target["enabled"]))
        if str(m.get("fan")) in P.FAN_PRESETS:
            target["fan"] = str(m["fan"])
        if str(m.get("pump")) in P.PUMP_PRESETS + ("default",):
            target["pump"] = str(m["pump"])
        target["boost"] = bool(m.get("boost", target["boost"]))
    return cfg


def load() -> dict:
    try:
        return _merge(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULTS)


def save(cfg: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG_FILE)
