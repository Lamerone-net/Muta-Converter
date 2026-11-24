"""Paths shared by source runs and packaged applications."""
from pathlib import Path
import sys


def icon_path() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "assets/branding/icon.ico"
