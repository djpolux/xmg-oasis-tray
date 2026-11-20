# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project

XMG OASIS Tray: unofficial Windows tray utility (Python >=3.10) for XMG laptops with the XMG OASIS external liquid cooler. Follows the operating mode selected in the XMG Control Center and applies a per-mode cooler setting (fan preset / pump voltage / boost).

- Version lives in `src/xmg_oasis_tray/__init__.py` (`__version__`, read dynamically by `pyproject.toml`).
- Dependencies: `paho-mqtt>=2,<3`, `pystray`, `Pillow`. Windows only.

## Commands

```powershell
# Install deps
python -m pip install -r requirements.txt

# Run from source (from the `src` folder, or with `src` on PYTHONPATH)
python -m xmg_oasis_tray

# Build single exe -> dist\XMG-OASIS-Tray.exe
# (PyInstaller onefile/windowed, entry packaging/launcher.py, needs --hidden-import pystray._win32)
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

- Release: pushing a tag `v*` triggers `.github/workflows/release.yml` (windows-latest, Python 3.12) which builds and publishes the exe.
- No test suite, no linter configured.
- Runtime data: `%APPDATA%\xmg-oasis-tray\config.json` and `oasis_tray.log` — check the log first when debugging (every publish logged as `-> topic payload`, refusals as `REFUSED`, broker connect/disconnect).

## Architecture (src/xmg_oasis_tray/)

- **protocol.py**: constants only — broker 127.0.0.1:13688, 20 plugin accounts (slot 0..19, `plugin_credentials()`), topics `Fan/Control`, `Fan/Status`, `Tray/Status`, `BT_LC/Control`, `BT_LC/Status`, modes "0" Office/Silent, "1" Gaming/Enthusiast, "2" Turbo/Overboost, "3" Custom, fan presets `FAN_PRESETS`/`FAN_DUTY`, pump `PUMP_PRESETS`/`PUMP_VOLT`, `ALLOWED` whitelist of `(topic, action)`, `MAIN_OPTION_JSON` path.
- **app.py**: `OasisTray` class. paho-mqtt client (`CallbackAPIVersion.VERSION2`, clean_session) runs in `loop_start()` thread; pystray `icon.run()` on main thread; a daemon thread `_watch_mode_file` polls MainOption.json as fallback. MQTT callbacks (`_on_connect`, `_on_message`) run on the paho thread and mutate state then call `refresh()`. State machine: `on_mode()` stores the pending mode until the first `BT_LC/Status` arrives, then `apply_mode_profile()`; `on_cooler_status()` records `initial_lc` and re-applies on Bluetooth reconnect. `publish()` checks `P.ALLOWED` and always sends qos=1, retain=False. Menu built in `_build_menu()`; pystray actions must be zero-arg -> use the `call(fn, *args)` helper.
- **config.py**: `DEFAULTS`, `load()`/`_merge()` validate every user value against protocol presets (invalid -> default), `save()` atomic via `.tmp` replace, `log()`.
- **i18n.py**: `tr(lang, key, **kw)`, languages "fr" and "en" — every new UI string needs both.
- **icons.py**: `make_icon(mode, online, boost)` draws the coloured letter icon with Pillow.
- **platform_win.py**: `single_instance()`, startup shortcut (`set_startup`), `open_path`.
- **docs/PROTOCOL.md**: reverse-engineered protocol notes (Control Center 5.9.50.2) — update it when protocol knowledge changes.

## Safety rules (must keep)

- Only send actions in `protocol.ALLOWED`. Never add FanOff / PumpOff (stops water flow), LCHWOC/Control (GPU overclock), firmware update or pairing reset.
- Never use the Control Center service's own MQTT client id (it would kick the service off the broker); only `PluginClient_n` slots.
- Always `retain=False`.
- The service accepts only presets: fan 40/50/60/90 %, pump duty 60 % (90 % only in boost), pump voltage 7/8/11 V. No free percentage.

## Conventions

- User-facing README is bilingual FR/EN; keep both sections in sync.
- Bump `__version__` in `__init__.py` for releases.
