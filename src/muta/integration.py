"""Per-user Windows Explorer integration. Only Muta-owned keys are modified."""

from __future__ import annotations
from .i18n import tr

import os
from pathlib import Path
import subprocess
import sys

from .catalog import FAMILIES, family_for, normalize
from .engines import ConversionError, find_engine, image_supported
from .settings import Settings
from .resources import icon_path

PREFIX = r"Software\Classes\SystemFileAssociations"
OWN_KEY = "MutaConverter"
FALLBACK_KEY = r"Software\Classes\*\shell\MutaNotMutable"


def not_mutable_condition(entries: dict) -> str:
    return "NOT (" + " OR ".join(f"System.FileExtension:=.{ext}" for ext in sorted(entries)) + ")" if entries else ""


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).with_name("Muta.exe" if os.name == "nt" else "Muta")
        return [str(executable)]
    executable = Path(sys.executable)
    if os.name == "nt" and executable.with_name("pythonw.exe").is_file():
        executable = executable.with_name("pythonw.exe")
    return [str(executable), "-m", "muta"]


def menu_entries(settings: Settings) -> dict[str, list[tuple[str, str, str]]]:
    settings.apply_engines()
    entries = {}
    base = launch_command()
    for family in FAMILIES:
        if family.engine != "pillow" and not find_engine(family.engine):
            continue
        for extension in family.inputs:
            items = []
            for preset in settings.presets:
                if (not preset.enabled or preset.family != family.name or extension not in preset.inputs
                        or normalize(extension) == preset.target):
                    continue
                if family.engine == "pillow" and not image_supported(extension, preset.target):
                    continue
                # Quote %1 explicitly, even though list2cmdline would not need to.
                command = subprocess.list2cmdline([*base, "convert", "--preset", preset.id, "--notify", "--"])
                items.append((preset.id, preset.display_name(settings.language), command + ' "%1"'))
            if items:
                entries[extension] = items
    return entries


def _require_windows():
    if os.name != "nt":
        raise ConversionError(tr("Il menu contestuale automatico è disponibile su Windows. Su macOS/Linux usa per ora l'interfaccia o la CLI."))
    import winreg
    return winreg


def _delete_tree(reg, path: str) -> None:
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, path, 0, reg.KEY_READ | reg.KEY_WRITE) as key:
            children = []
            index = 0
            while True:
                try:
                    children.append(reg.EnumKey(key, index))
                    index += 1
                except OSError as exc:
                    if getattr(exc, "winerror", None) == 259:
                        break
                    raise
        for child in children:
            _delete_tree(reg, path + "\\" + child)
        reg.DeleteKey(reg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def remove_menu() -> None:
    reg = _require_windows()
    _delete_tree(reg, FALLBACK_KEY)
    for family in FAMILIES:
        for extension in family.inputs:
            _delete_tree(reg, f"{PREFIX}\\.{extension}\\shell\\{OWN_KEY}")
    _notify_shell()


def menu_installed() -> bool:
    if os.name != "nt":
        return False
    reg = _require_windows()
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, FALLBACK_KEY):
            return True
    except FileNotFoundError:
        pass
    for family in FAMILIES:
        for extension in family.inputs:
            try:
                with reg.OpenKey(reg.HKEY_CURRENT_USER, f"{PREFIX}\\.{extension}\\shell\\{OWN_KEY}"):
                    return True
            except FileNotFoundError:
                pass
    return False


def install_menu(settings: Settings) -> None:
    reg = _require_windows()
    entries = menu_entries(settings)
    # Build and validate everything before replacing any installed menu.
    remove_menu()
    def value(path, name, data):
        with reg.CreateKey(reg.HKEY_CURRENT_USER, path) as key:
            reg.SetValueEx(key, name, 0, reg.REG_SZ, data)
    value(FALLBACK_KEY, "MUIVerb", tr('Not mutable', language=settings.language))
    value(FALLBACK_KEY, "MultiSelectModel", "Single")
    if entries:
        value(FALLBACK_KEY, "AppliesTo", not_mutable_condition(entries))
    command = subprocess.list2cmdline([*launch_command(), "not-mutable", "--"])
    value(FALLBACK_KEY + "\\command", "", command + ' "%1"')
    for extension, items in entries.items():
        root = f"{PREFIX}\\.{extension}\\shell\\{OWN_KEY}"
        value(root, "MUIVerb", tr('Muta · Converti in', language=settings.language))
        value(root, "SubCommands", "")
        value(root, "MultiSelectModel", "Single")
        value(root, "Icon", subprocess.list2cmdline([str(icon_path())]))
        for index, (identifier, name, command) in enumerate(items):
            key = f"{root}\\shell\\{index:03}_{identifier}"
            value(key, "MUIVerb", name)
            value(key, "MultiSelectModel", "Single")
            value(key + "\\command", "", command)
        key = root + r"\shell\999_preferences"
        value(key, "MUIVerb", tr('Preferences…', language=settings.language))
        value(key, "SeparatorBefore", "")
        value(key + "\\command", "", subprocess.list2cmdline([*launch_command(), "--preferences"]))
    _notify_shell()


def _notify_shell() -> None:
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def set_autostart(enabled: bool) -> None:
    reg = _require_windows()
    with reg.CreateKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            reg.SetValueEx(key, OWN_KEY, 0, reg.REG_SZ,
                           subprocess.list2cmdline([*launch_command(), "--tray"]))
        else:
            try:
                reg.DeleteValue(key, OWN_KEY)
            except FileNotFoundError:
                pass
