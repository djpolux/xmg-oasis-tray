"""PyInstaller entry point (the package uses relative imports)."""
import sys

from xmg_oasis_tray.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
