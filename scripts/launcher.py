"""PyInstaller entry point for both GUI and CLI executables."""
from muta.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
