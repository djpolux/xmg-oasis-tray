import sys

from .platform_win import single_instance


def main() -> int:
    if sys.platform != "win32":
        print("XMG OASIS Tray only runs on Windows.")
        return 1
    if not single_instance():
        return 0
    from .app import OasisTray
    OasisTray().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
