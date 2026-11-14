# XMG OASIS Tray

**[Français](#français) · [English](#english)**

Unofficial tray utility for XMG laptops with the **XMG OASIS** external liquid
cooler. It follows the operating mode selected in the XMG Control Center and sets
the cooler (fan / pump / boost) you chose for that mode.

> Not affiliated with XMG, Schenker Technologies, Uniwill or their partners.
> Use at your own risk.

---

## Français

### Ce que fait l'outil
- Icône dans la zone de notification (à côté de l'horloge), couleur = mode du PC :
  bleu **S**ilencieux, vert **E**nthusiast, rouge **O**verboost, violet **P**ersonnalisé.
- **Suit les modes du PC** : à chaque changement (Control Center ou touche Fn), il
  applique le réglage du refroidisseur choisi pour ce mode.
- **Clic droit** : état du PC et de l'OASIS, réglage manuel (ventilateur 40 / 60 /
  90 %, auto), **Boost** (pompe + ventilateur 90 %), **tension de pompe** (7 / 8 / 11 V),
  changement de mode du PC, et tous les **réglages**.

### Réglages (menu Réglages)
| Réglage | Effet |
|---|---|
| Suivre les modes du PC | Active / désactive tout le suivi automatique |
| Réglage par mode | Pour chaque mode : suivre ou non, ventilateur, pompe, boost |
| Notifications | Bulle Windows à chaque changement de mode |
| Réappliquer à la reconnexion | Réapplique le réglage quand l'OASIS se reconnecte en Bluetooth |
| Surveiller le fichier de mode | Détection de secours des changements de mode |
| Restaurer l'état initial | Remet le réglage d'origine de l'OASIS en quittant |
| Langue | Français / English |
| Lancer au démarrage de Windows | Ajoute / retire le raccourci de démarrage |

Réglages par défaut : Silencieux → 40 %, Enthusiast → 60 %, Overboost → 90 %,
Personnalisé → Boost 90 % / 90 %.

### Installation (aucun prérequis)
1. Télécharge `XMG-OASIS-Tray.exe` dans la page **Releases**.
2. Lance-le. L'icône apparaît près de l'horloge (sinon dans la flèche **^**).
3. Clic droit → Réglages → **Lancer au démarrage de Windows**.

Le XMG Control Center doit être installé et l'OASIS appairé dans celui-ci.
Windows SmartScreen peut avertir (exécutable non signé) : « Informations
complémentaires » → « Exécuter quand même ».

### Limites
Le service XMG n'accepte que des valeurs prédéfinies : ventilateur 40 / 50 / 60 /
90 %, pompe 60 % (90 % uniquement en Boost), tension de pompe 7 / 8 / 11 V.

---

## English

### What it does
- Tray icon next to the clock, colour = PC mode: blue **S**ilent, green
  **E**nthusiast, red **O**verboost, purple **P**ersonal/Custom.
- **Follows the PC modes**: on every change (Control Center or Fn hotkey) it applies
  the cooler setting chosen for that mode.
- **Right click**: PC and OASIS status, manual control (fan 40 / 60 / 90 %, auto),
  **Boost** (pump + fan 90 %), **pump voltage** (7 / 8 / 11 V), PC mode switch and all
  **settings** (per-mode fan / pump / boost / enabled, notifications, re-apply on
  reconnection, mode-file fallback, restore on exit, language, start with Windows).

### Install (nothing else needed)
1. Download `XMG-OASIS-Tray.exe` from **Releases**.
2. Run it; the icon appears near the clock (or under the **^** arrow).
3. Right click → Settings → **Start with Windows**.

Requires the XMG Control Center with the OASIS paired in it.

### Limits
The XMG service only accepts presets: fan 40 / 50 / 60 / 90 %, pump 60 % (90 % in
boost only), pump voltage 7 / 8 / 11 V.

---

## Safety
The tool can only send a whitelist of commands (fan preset, pump voltage, boost,
operating mode, status request). It never stops the pump or the fan, never applies
the GPU overclock exposed by the same service, and never touches firmware update or
pairing. Every command is sent with `retain=false`.

## How it works
The XMG Control Center service runs a local MQTT broker and reserves "plugin"
accounts for third-party tools. See [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Build from source
```powershell
python -m pip install -r requirements.txt
python -m xmg_oasis_tray            # run from the src folder
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # build the .exe
```
Settings and log: `%APPDATA%\xmg-oasis-tray\` (`config.json`, `oasis_tray.log`).

## License
MIT — see [LICENSE](LICENSE).
