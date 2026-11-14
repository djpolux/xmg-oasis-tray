"""Control Center (Uniwill / XMG) local MQTT protocol — values observed for interop.

The XMG Control Center service ("GCUBridge") hosts an MQTT broker on localhost
and reserves twenty "plugin" accounts for third-party tools. This module only
holds the topics, actions and preset values this application is allowed to use.
See docs/PROTOCOL.md for details.
"""

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 13688
PLUGIN_SLOTS = range(20)


def plugin_credentials(slot: int):
    """Plugin account for a given slot (0..19), as provisioned by the service."""
    if slot not in PLUGIN_SLOTS:
        raise ValueError("plugin slot must be between 0 and 19")
    return (f"PluginClient_{slot}",
            f"PluginClient_User_{slot}",
            f"PluginClient_Pwd888881772688_{slot}")


# ---- topics
T_FAN_CONTROL = "Fan/Control"      # operating mode switch / status request
T_FAN_STATUS = "Fan/Status"        # service -> clients, contains "OperatingMode"
T_TRAY_STATUS = "Tray/Status"      # service -> clients, contains "OperatingMode"
T_LC_CONTROL = "BT_LC/Control"     # liquid cooler (OASIS) commands
T_LC_STATUS = "BT_LC/Status"       # liquid cooler state

# ---- operating modes (value of "OperatingMode")
MODE_OFFICE, MODE_GAMING, MODE_TURBO, MODE_CUSTOM = "0", "1", "2", "3"
MODE_ORDER = (MODE_OFFICE, MODE_GAMING, MODE_TURBO, MODE_CUSTOM)
MODE_ACTIONS = {
    MODE_OFFICE: "OPERATING_OFFICE_MODE",
    MODE_GAMING: "OPERATING_GAMING_MODE",
    MODE_TURBO: "OPERATING_TURBO_MODE",
    MODE_CUSTOM: "OPERATING_CUSTOM_MODE",
}

# ---- liquid cooler presets ("FanCtrl" of LC_FanCtrl) — the service accepts no
# free percentage: fan 40 / 50 / 60 / 90 %, pump duty 60 % (90 % only in boost).
FAN_PRESETS = ("0", "2", "3", "1", "4")
FAN_DUTY = {"0": 40, "1": 50, "2": 60, "3": 90, "4": 60}
FAN_AUTO = {"1", "4"}              # EC driven, reported unreliable on some units

# "PumpCtrl" of LC_PumpCtrl -> pump voltage
PUMP_PRESETS = ("0", "1", "2")
PUMP_VOLT = {"0": 7, "1": 8, "2": 11}

# Whitelist: the only (topic, action) pairs this application may publish.
# Deliberately excluded: FanOff / PumpOff (stops water flow), LCHWOC/Control
# (applies a GPU overclock), firmware update and pairing reset actions.
ALLOWED = {
    T_LC_CONTROL: {"LC_FanCtrl", "LC_PumpCtrl", "LC_FanBoost", "GETSTATUS"},
    T_FAN_CONTROL: set(MODE_ACTIONS.values()) | {"GETSTATUS"},
}

# Where the service stores the active mode (read-only fallback for change detection)
MAIN_OPTION_JSON = (r"C:\Program Files\OEM\Control Center\UniwillService"
                    r"\MyControlCenter\UserPofiles\MainOption.json")
