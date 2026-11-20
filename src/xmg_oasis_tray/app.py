"""Tray application: follows the Control Center operating mode and drives the
XMG OASIS liquid cooler through the service's local MQTT broker."""
import json
import threading
from pathlib import Path

import paho.mqtt.client as mqtt
import pystray

from . import __version__
from . import config as C
from . import platform_win as W
from . import protocol as P
from .i18n import tr
from .icons import make_icon

Item, Menu = pystray.MenuItem, pystray.Menu


def call(fn, *args):
    """Zero-argument action for pystray (it inspects the action's arity)."""
    return lambda: fn(*args)


class OasisTray:
    def __init__(self):
        self.cfg = C.load()
        self.mode = None            # current OperatingMode ("0".."3")
        self.pending_mode = None    # mode seen before the first cooler status
        self.lc = {}                # last BT_LC/Status payload
        self.initial_lc = None      # cooler state found at start-up (restore option)
        self.broker_ok = False
        self.boost = False
        self._file_mode = None      # last value read from the mode file (fallback watcher)
        self._stop = threading.Event()
        self.icon = pystray.Icon("xmg_oasis_tray", make_icon(None, False), W.APP_NAME,
                                 menu=self._build_menu())
        b = self.cfg["broker"]
        client_id, user, pwd = P.plugin_credentials(b["plugin_slot"])
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                                  clean_session=True)
        self.client.username_pw_set(user, pwd)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(2, 30)

    # ------------------------------------------------------------ helpers
    def t(self, key, **kw):
        return tr(self.cfg["language"], key, **kw)

    def mode_label(self, mode):
        return self.t(f"mode.{mode}") if mode in P.MODE_ACTIONS else self.t("status.unknown")

    def save(self):
        C.save(self.cfg)
        self.refresh()

    # ------------------------------------------------------------ MQTT
    def publish(self, topic, payload):
        if payload.get("Action") not in P.ALLOWED.get(topic, set()):
            C.log(f"REFUSED {topic} {payload}")
            return
        self.client.publish(topic, json.dumps(payload), qos=1, retain=False)
        C.log(f"-> {topic} {payload}")

    def _on_connect(self, client, userdata, flags, rc, props=None):
        self.broker_ok = not rc.is_failure
        C.log(f"broker connected: {rc}")
        if self.broker_ok:
            client.subscribe([(P.T_FAN_STATUS, 0), (P.T_TRAY_STATUS, 0), (P.T_LC_STATUS, 0)])
            self.publish(P.T_LC_CONTROL, {"Action": "GETSTATUS"})
            self.publish(P.T_FAN_CONTROL, {"Action": "GETSTATUS"})
        self.refresh()

    def _on_disconnect(self, client, userdata, flags, rc, props=None):
        self.broker_ok = False
        C.log(f"broker disconnected: {rc}")
        self.refresh()

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8", "replace"))
        except ValueError:
            return
        if msg.topic in (P.T_FAN_STATUS, P.T_TRAY_STATUS) and "OperatingMode" in data:
            self.on_mode(str(data["OperatingMode"]))
        elif msg.topic == P.T_LC_STATUS:
            self.on_cooler_status(data)

    # ------------------------------------------------------------ state machine
    def on_cooler_status(self, data):
        was_connected = bool(self.lc.get("connected"))
        first = not self.lc
        self.lc = data
        now_connected = bool(data.get("connected"))
        if was_connected and not now_connected:
            self.boost = False
            C.log("cooler disconnected")
        if first and self.initial_lc is None:
            self.initial_lc = {"fan": str(data.get("LC_FanCtrl", "")),
                               "pump": str(data.get("LC_PumpCtrl", ""))}
            C.log(f"initial cooler state: {self.initial_lc}")
        if first and self.pending_mode:
            mode, self.pending_mode = self.pending_mode, None
            self.apply_mode_profile(mode, "start-up")
        elif (not was_connected and now_connected and not first
              and self.cfg["reapply_on_reconnect"] and self.mode):
            self.apply_mode_profile(self.mode, "cooler reconnected")
        self.refresh()

    def on_mode(self, mode):
        if mode not in P.MODE_ACTIONS or mode == self.mode:
            return
        first = self.mode is None
        self.mode = mode
        C.log(f"PC mode: {mode}")
        if not self.lc:                     # wait for the cooler state first
            self.pending_mode = mode
        else:
            self.apply_mode_profile(mode, "start-up" if first else "mode change")
        self.refresh()

    def apply_mode_profile(self, mode, reason):
        prof = self.cfg["modes"][mode]
        if not self.cfg["follow"]:
            return
        if not prof["enabled"]:
            if reason == "mode change":
                self.notify(self.t("notify.skip", m=self.mode_label(mode)))
            return
        self.apply_cooler(prof["fan"], prof["pump"], prof["boost"], reason)
        if reason == "mode change":
            self.notify(self.t("notify.mode", m=self.mode_label(mode), s=self.profile_short(prof)))

    def cooler_ready(self):
        """False when the last cooler status says it is disconnected (Bluetooth)."""
        if self.lc and not self.lc.get("connected"):
            C.log("cooler not connected: nothing sent")
            return False
        return True

    def apply_cooler(self, fan, pump="default", boost=False, reason="manual"):
        if not self.cooler_ready():
            return
        if not boost:
            # always clear boost first: it may have been left on (previous session,
            # Fn hotkey) and it overrides the pump/fan duty of the presets
            self.set_boost(False)
        self.publish(P.T_LC_CONTROL, {"Action": "LC_FanCtrl", "FanCtrl": fan})
        if pump in P.PUMP_PRESETS:
            self.publish(P.T_LC_CONTROL, {"Action": "LC_PumpCtrl", "PumpCtrl": pump})
        if boost:
            self.set_boost(True)
        C.log(f"cooler fan={fan} pump={pump} boost={boost} ({reason})")

    def set_boost(self, on):
        if not self.cooler_ready():
            self.refresh()
            return
        self.boost = bool(on)
        self.publish(P.T_LC_CONTROL, {"Action": "LC_FanBoost", "IsEnable": self.boost})
        self.refresh()

    def set_pump(self, pump):
        if self.cooler_ready():
            self.publish(P.T_LC_CONTROL, {"Action": "LC_PumpCtrl", "PumpCtrl": pump})

    def profile_short(self, prof):
        if prof["boost"]:
            return "Boost 90/90"
        s = self.t(f"fan.short.{prof['fan']}")
        if prof["pump"] in P.PUMP_PRESETS:
            s += f" / {P.PUMP_VOLT[prof['pump']]} V"
        return s

    # ------------------------------------------------------------ mode file fallback
    def _watch_mode_file(self):
        path = Path(P.MAIN_OPTION_JSON)
        while not self._stop.wait(self.cfg["watch_interval_s"]):
            if not self.cfg["watch_mode_file"] or not path.exists():
                continue
            try:
                mode = str(json.loads(path.read_text(encoding="utf-8-sig")).get("OperatingMode"))
            except (OSError, ValueError):
                continue
            if mode not in P.MODE_ACTIONS:
                continue
            previous, self._file_mode = self._file_mode, mode
            # only react when the file itself changed (a change MQTT missed);
            # a file that merely lags behind MQTT must not revert the mode
            if previous is not None and mode != previous and mode != self.mode and self.mode is not None:
                C.log(f"mode file says {mode}")
                self.on_mode(mode)

    # ------------------------------------------------------------ user actions
    def switch_pc_mode(self, mode):
        idx = 0
        if mode == P.MODE_CUSTOM:
            try:
                idx = int(json.loads(Path(P.MAIN_OPTION_JSON).read_text(encoding="utf-8-sig"))
                          .get("CustomProfileIndex", 0))
            except (OSError, ValueError):
                idx = 0
        self.publish(P.T_FAN_CONTROL, {"Action": P.MODE_ACTIONS[mode], "ProfileIndex": idx})

    def set_mode_field(self, mode, field, value):
        self.cfg["modes"][mode][field] = value
        self.save()
        if self.mode == mode:
            self.apply_mode_profile(mode, "setting changed")

    def toggle(self, key):
        self.cfg[key] = not self.cfg[key]
        self.save()
        if key == "follow" and self.cfg["follow"] and self.mode:
            self.apply_mode_profile(self.mode, "following re-enabled")

    def set_language(self, lang):
        self.cfg["language"] = lang
        self.save()

    def toggle_startup(self):
        W.set_startup(not W.startup_shortcut().exists())
        self.refresh()

    def notify(self, text):
        if self.cfg["notify"]:
            try:
                self.icon.notify(text, W.APP_NAME)
            except Exception:  # notifications are best effort
                pass

    # ------------------------------------------------------------ menu
    def _status_line(self):
        if not self.broker_ok:
            return self.t("status.nobroker")
        return self.t("status.mode", m=self.mode_label(self.mode))

    def _cooler_line(self):
        if not self.lc:
            return self.t("status.lc.wait")
        if not self.lc.get("connected"):
            return self.t("status.lc.off")
        volt = P.PUMP_VOLT.get(str(self.lc.get("LC_PumpCtrl")), "?")
        return self.t("status.lc", f=self.lc.get("FanDuty", "?"), p=self.lc.get("PumpDuty", "?"),
                      v=volt, b="  [BOOST]" if self.boost else "")

    def _build_menu(self):
        def radio(text, action, is_checked, enabled=True):
            return Item(text, action, checked=is_checked, radio=True, enabled=enabled)

        connected = lambda i: bool(self.lc.get("connected"))   # noqa: E731

        def manual_fan(level):
            return radio(lambda i: self.t(f"fan.{level}"),
                         lambda: self.apply_cooler(level, "default", False),
                         lambda i: str(self.lc.get("LC_FanCtrl")) == level and not self.boost,
                         connected)

        def manual_pump(v):
            return radio(lambda i: self.t("pump.v", v=P.PUMP_VOLT[v]),
                         lambda: self.set_pump(v),
                         lambda i: str(self.lc.get("LC_PumpCtrl")) == v,
                         connected)

        def mode_profile(mode):
            prof = lambda: self.cfg["modes"][mode]   # noqa: E731
            fan_items = [radio(lambda i, l=lvl: self.t(f"fan.{l}"),
                               call(self.set_mode_field, mode, "fan", lvl),
                               lambda i, l=lvl: prof()["fan"] == l) for lvl in P.FAN_PRESETS]
            pump_items = [radio(lambda i: self.t("pump.default"),
                                lambda: self.set_mode_field(mode, "pump", "default"),
                                lambda i: prof()["pump"] == "default")]
            pump_items += [radio(lambda i, v=v: self.t("pump.v", v=P.PUMP_VOLT[v]),
                                 call(self.set_mode_field, mode, "pump", v),
                                 lambda i, v=v: prof()["pump"] == v) for v in P.PUMP_PRESETS]
            return Item(lambda i: self.mode_label(mode), Menu(
                Item(lambda i: self.t("menu.profile.use"),
                     lambda: self.set_mode_field(mode, "enabled", not prof()["enabled"]),
                     checked=lambda i: prof()["enabled"]),
                Item(lambda i: self.t("menu.profile.fan"), Menu(*fan_items)),
                Item(lambda i: self.t("menu.profile.pump"), Menu(*pump_items)),
                Item(lambda i: self.t("menu.mode.boost"),
                     lambda: self.set_mode_field(mode, "boost", not prof()["boost"]),
                     checked=lambda i: prof()["boost"]),
            ))

        def toggle_item(key, label):
            return Item(lambda i: self.t(label), lambda: self.toggle(key),
                        checked=lambda i: self.cfg[key])

        return Menu(
            Item(lambda i: self._status_line(), None, enabled=False),
            Item(lambda i: self._cooler_line(), None, enabled=False),
            Menu.SEPARATOR,
            Item(lambda i: self.t("menu.pcmode"), Menu(*[
                radio(lambda i, m=m: self.mode_label(m), call(self.switch_pc_mode, m),
                      lambda i, m=m: self.mode == m) for m in P.MODE_ORDER])),
            Item(lambda i: self.t("menu.manual") if self.lc.get("connected") else self.t("menu.manual.off"), Menu(
                Item(lambda i: self.t("menu.manual.fan"), Menu(*[manual_fan(l) for l in P.FAN_PRESETS]),
                     enabled=connected),
                Item(lambda i: self.t("menu.manual.pump"), Menu(*[manual_pump(v) for v in P.PUMP_PRESETS]),
                     enabled=connected),
                Menu.SEPARATOR,
                Item(lambda i: self.t("menu.boost"), lambda: self.set_boost(not self.boost),
                     checked=lambda i: self.boost, enabled=connected),
            )),
            Menu.SEPARATOR,
            Item(lambda i: self.t("menu.profiles"), Menu(*[mode_profile(m) for m in P.MODE_ORDER])),
            Item(lambda i: self.t("menu.settings"), Menu(
                toggle_item("follow", "menu.follow"),
                Menu.SEPARATOR,
                toggle_item("notify", "menu.notify"),
                toggle_item("reapply_on_reconnect", "menu.reapply"),
                toggle_item("watch_mode_file", "menu.watch"),
                toggle_item("restore_on_exit", "menu.restore"),
                Item(lambda i: self.t("menu.lang"), Menu(
                    radio("Français", lambda: self.set_language("fr"), lambda i: self.cfg["language"] == "fr"),
                    radio("English", lambda: self.set_language("en"), lambda i: self.cfg["language"] == "en"),
                )),
                Item(lambda i: self.t("menu.startup"), lambda: self.toggle_startup(),
                     checked=lambda i: W.startup_shortcut().exists()),
                Menu.SEPARATOR,
                Item(lambda i: self.t("menu.opencfg"), lambda: (C.save(self.cfg), W.open_path(C.CONFIG_FILE))),
                Item(lambda i: self.t("menu.openlog"), lambda: W.open_path(C.LOG_FILE)),
            )),
            Menu.SEPARATOR,
            Item(lambda i: f"{self.t('menu.quit')} (v{__version__})", lambda: self.quit()),
        )

    def refresh(self):
        try:
            online = self.broker_ok and bool(self.lc.get("connected", True))
            self.icon.icon = make_icon(self.mode, online, self.boost)
            fan = "Boost" if self.boost else self.t(f"fan.short.{self.lc.get('LC_FanCtrl', '')}")
            self.icon.title = f"{W.APP_NAME}\n{self.mode_label(self.mode)} - OASIS {fan}"[:127]
            self.icon.update_menu()
        except Exception:
            pass

    # ------------------------------------------------------------ lifecycle
    def quit(self):
        C.log("exit")
        self._stop.set()
        try:
            if self.cfg["restore_on_exit"] and self.initial_lc and self.initial_lc["fan"] in P.FAN_PRESETS:
                if self.boost:
                    self.set_boost(False)
                pump = self.initial_lc["pump"] if self.initial_lc["pump"] in P.PUMP_PRESETS else "default"
                self.apply_cooler(self.initial_lc["fan"], pump, False, "restore on exit")
            self.client.loop_stop()
            self.client.disconnect()
        finally:
            self.icon.stop()

    def run(self):
        C.log(f"start v{__version__}")
        b = self.cfg["broker"]
        self.client.connect_async(b["host"], b["port"], keepalive=30)
        self.client.loop_start()
        threading.Thread(target=self._watch_mode_file, daemon=True).start()
        self.icon.run()
