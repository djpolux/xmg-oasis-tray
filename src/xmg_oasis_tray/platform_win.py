"""Windows helpers: single instance, start-up shortcut, open files."""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "XMG OASIS Tray"
_mutex = None


def single_instance() -> bool:
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\XMG_OASIS_Tray_single")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def startup_shortcut() -> Path:
    return (Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu"
            / "Programs" / "Startup" / f"{APP_NAME}.lnk")


def _launch_command():
    """(target, arguments, working dir) used for the start-up shortcut."""
    if getattr(sys, "frozen", False):          # PyInstaller build
        exe = Path(sys.executable)
        return exe, "", exe.parent
    pyw = Path(sys.executable).with_name("pythonw.exe")
    target = pyw if pyw.exists() else Path(sys.executable)
    pkg_root = Path(__file__).resolve().parents[1]   # .../src
    return target, "-m xmg_oasis_tray", pkg_root


def set_startup(enabled: bool) -> None:
    lnk = startup_shortcut()
    if not enabled:
        if lnk.exists():
            lnk.unlink()
        return
    target, args, cwd = _launch_command()
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
          "$s.TargetPath=$env:TGT;$s.Arguments=$env:ARGS;$s.WorkingDirectory=$env:CWD;"
          "$s.Description='XMG OASIS Tray';$s.Save()")
    env = dict(os.environ, LNK=str(lnk), TGT=str(target), ARGS=args, CWD=str(cwd))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   env=env, creationflags=0x08000000, check=False)


def open_path(path: Path) -> None:
    if path.exists():
        os.startfile(str(path))  # noqa: S606 - opens with the default editor
