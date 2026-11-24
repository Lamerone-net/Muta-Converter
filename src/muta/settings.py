"""Versioned per-user preferences; portable config location for tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

from .catalog import FAMILIES, format_label
from .engines import ConversionError
from .service import Options

_ENGINE_KEYS = {"ffmpeg": "MUTA_FFMPEG", "libreoffice": "MUTA_LIBREOFFICE", "sevenzip": "MUTA_7ZIP"}
_ORIGINAL_ENGINE_ENV = {key: os.environ.get(key) for key in _ENGINE_KEYS.values()}


def config_dir() -> Path:
    override = os.environ.get("MUTA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "MutaConverter"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/MutaConverter"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "muta-converter"


@dataclass
class Preset:
    id: str
    name: str
    family: str
    target: str
    inputs: list[str]
    enabled: bool = True
    options: Options = field(default_factory=Options)

    def validate(self) -> None:
        family = next((f for f in FAMILIES if f.name == self.family), None)
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", self.id):
            raise ConversionError("Identificatore preset non valido.")
        if not self.name.strip() or len(self.name) > 80:
            raise ConversionError("Il nome del preset deve contenere da 1 a 80 caratteri.")
        if not family or self.target not in family.outputs or not self.inputs or not set(self.inputs) <= set(family.inputs):
            raise ConversionError("Formati del preset non validi.")
        self.options.validate()


def default_presets() -> list[Preset]:
    return [Preset(f"{family.name}_{target}", format_label(target), family.name,
                   target, list(family.inputs)) for family in FAMILIES for target in family.outputs]


@dataclass
class Settings:
    presets: list[Preset] = field(default_factory=default_presets)
    output_dir: str = ""
    ffmpeg: str = ""
    libreoffice: str = ""
    sevenzip: str = ""
    autostart: bool = False
    check_updates_on_start: bool = False

    def preset(self, identifier: str) -> Preset:
        found = next((p for p in self.presets if p.id == identifier), None)
        if not found or not found.enabled:
            raise ConversionError("Preset assente o disabilitato. Aggiorna il menu dalle preferenze.")
        return found

    def apply_engines(self) -> None:
        for name, key in _ENGINE_KEYS.items():
            value = getattr(self, name)
            if value:
                os.environ[key] = value
            else:
                original = _ORIGINAL_ENGINE_ENV[key]
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original


def load_settings() -> Settings:
    path = config_dir() / "settings.json"
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        schema = data.pop("version", None)
        if schema not in (1, 2):
            raise ValueError("Versione preferenze non supportata")
        presets = []
        for item in data.pop("presets"):
            item["options"] = Options(**item.get("options", {}))
            preset = Preset(**item)
            if preset.id == f"{preset.family}_{preset.target}" and preset.name == f"In {preset.target.upper()}":
                preset.name = format_label(preset.target)
            preset.validate()
            presets.append(preset)
        # Add archive presets to configurations saved before archive support existed.
        if schema == 1 and not any(p.family == "archive" for p in presets):
            presets.extend(p for p in default_presets() if p.family == "archive")
        settings = Settings(presets=presets, **data)
        if len({p.id for p in presets}) != len(presets):
            raise ValueError("Identificatori duplicati")
        return settings
    except (ValueError, TypeError, KeyError, OSError, ConversionError) as exc:
        raise ConversionError(f"Preferenze non leggibili: {path}\n{exc}") from exc


def save_settings(settings: Settings) -> None:
    for preset in settings.presets:
        preset.validate()
    if len({p.id for p in settings.presets}) != len(settings.presets):
        raise ConversionError("Identificatori preset duplicati.")
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix="settings-", suffix=".json", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"version": 2, **asdict(settings)}, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / "settings.json")
    finally:
        Path(temporary).unlink(missing_ok=True)


def clone_preset(preset: Preset) -> Preset:
    return Preset(uuid.uuid4().hex, preset.name + " (copia)", preset.family,
                  preset.target, list(preset.inputs), preset.enabled, preset.options)
