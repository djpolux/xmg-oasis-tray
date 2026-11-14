# XMG Control Center — local protocol notes (interoperability)

Observed on Control Center 5.9.50.2 (XMG branch, OASIS firmware LCT22002 v2.0.0.4).
Values may change between Control Center versions.

## Transport
- The `GCUBridge` Windows service hosts an MQTT broker on `127.0.0.1:13688`.
- It provisions 20 plugin accounts for third-party tools (slot `n` = 0..19):
  client id `PluginClient_n`, user `PluginClient_User_n`,
  password `PluginClient_Pwd888881772688_n`.
- Never connect with the client id used by the Control Center service itself: MQTT
  would disconnect the service.
- Payloads are JSON. Publish with `retain=false` (the broker keeps sessions).

## Operating mode
- Status: `Fan/Status` and `Tray/Status` contain `"OperatingMode"` as a string:
  `"0"` Office, `"1"` Gaming, `"2"` Turbo, `"3"` Custom.
- Switch: `Fan/Control` with `{"Action":"OPERATING_<OFFICE|GAMING|TURBO|CUSTOM>_MODE","ProfileIndex":n}`.
- Request status: `Fan/Control` `{"Action":"GETSTATUS"}`.
- The active mode is also written to `...\UserPofiles\MainOption.json` (`OperatingMode`).

## OASIS liquid cooler
- Status: `BT_LC/Status` (`connected`, `FanDuty`, `PumpDuty`, `LC_FanCtrl`,
  `LC_PumpCtrl`, `LC_CoolingAuto`, ...). Request with `BT_LC/Control` `{"Action":"GETSTATUS"}`.
- Fan preset: `BT_LC/Control` `{"Action":"LC_FanCtrl","FanCtrl":"<n>"}` (string):

  | FanCtrl | Effect |
  |---|---|
  | "0" | fan 40 %, pump 7 V (quiet) |
  | "1" | EC-driven auto (fan ~50 %), pump 8 V |
  | "2" | fan 60 % |
  | "3" | fan 90 % |
  | "4" | auto |

- Pump voltage: `{"Action":"LC_PumpCtrl","PumpCtrl":"0|1|2"}` → 7 / 8 / 11 V (duty stays 60 %).
- Boost: `{"Action":"LC_FanBoost","IsEnable":true|false}` → pump 90 % + fan 90 % (not persisted).
- No free percentage is accepted through the service.

## Do not use
- `FanOff` / `PumpOff`: really stop the fan / pump (no water flow).
- `LCHWOC/Control`: selects an EC fan table and can apply a GPU core/memory overclock.
- Firmware update and pairing reset actions.
