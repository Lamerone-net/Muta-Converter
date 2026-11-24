"""Shared conversion API. Inputs are immutable; output names never overwrite files."""

from __future__ import annotations
from .i18n import tr

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile

from .catalog import family_for, normalize
from .engines import (ConversionError, convert_image, convert_media, convert_office,
                      find_engine, image_supported)


@dataclass(frozen=True)
class Options:
    quality: int = 90
    first_frame: bool = False
    timeout: int = 1800
    scale: int = 100
    rotation: int = 0
    background: str = "#ffffff"
    video_crf: int = 23
    video_preset: str = "medium"
    audio_bitrate: int = 192
    include_audio: bool = True
    pdf_quality: int = 90
    pdf_lossless: bool = False
    csv_separator: str = ","
    name_template: str = "{name}"
    archive_level: int = 6
    archive_limit_mb: int = 2048
    archive_max_files: int = 100000

    def validate(self) -> None:
        from PIL import ImageColor
        ranges = ((self.quality, 1, 100), (self.timeout, 1, 86400),
                  (self.scale, 1, 200), (self.video_crf, 0, 51),
                  (self.audio_bitrate, 32, 320), (self.pdf_quality, 1, 100),
                  (self.archive_level, 0, 9), (self.archive_limit_mb, 1, 1048576),
                  (self.archive_max_files, 1, 1000000))
        if any(type(value) is not int or not low <= value <= high for value, low, high in ranges):
            raise ConversionError(tr('Uno dei parametri numerici è fuori intervallo.'))
        if self.rotation not in (0, 90, 180, 270):
            raise ConversionError(tr('Rotazione consentita: 0, 90, 180, 270 gradi.'))
        if self.video_preset not in ("ultrafast", "fast", "medium", "slow", "veryslow"):
            raise ConversionError(tr('Preset video non valido.'))
        if self.csv_separator not in (",", ";", "\t"):
            raise ConversionError(tr('Separatore CSV non valido.'))
        try:
            ImageColor.getrgb(self.background)
        except (ValueError, TypeError) as exc:
            raise ConversionError(tr('Colore di sfondo non valido (esempio: #ffffff).')) from exc
        output_stem("esempio", "jpg", self.name_template)


def output_stem(stem: str, target: str, template: str) -> str:
    if not isinstance(template, str):
        raise ConversionError(tr('Modello nome file non valido.'))
    value = template.replace("{name}", stem).replace("{format}", target)
    if (not value.strip() or any(c in value for c in '<>:"/\\|?*{}')
            or any(ord(c) < 32 for c in value) or value.endswith((".", " "))
            or value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
        raise ConversionError(tr('Nome file non valido. Usa {name} e {format}, senza cartelle.'))
    return value


def targets_for(source: Path, available_only: bool = True) -> list[str]:
    family = family_for(source.suffix)
    if not family:
        return []
    targets = [target for target in family.outputs if target != normalize(source.suffix)]
    if not available_only:
        return targets
    if family.engine == "pillow":
        return [t for t in targets if image_supported(source.suffix.lstrip("."), t)]
    return targets if find_engine(family.engine) else []


def publish(staged: Path, directory: Path, stem: str, target: str) -> Path:
    """Exclusive creation handles concurrent Explorer jobs and existing files."""
    for number in range(10000):
        suffix = "" if number == 0 else f" ({number})"
        output = directory / f"{stem}{suffix}.{target}"
        try:
            stream = output.open("xb")
        except FileExistsError:
            continue
        try:
            with stream, staged.open("rb") as source:
                shutil.copyfileobj(source, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            output.unlink(missing_ok=True)
            raise
        return output
    raise ConversionError(tr('Troppi file con lo stesso nome nella cartella di destinazione.'))


def convert(source: Path | str, target: str, output_dir: Path | None = None,
            options: Options = Options()) -> Path:
    source = Path(source).expanduser().resolve()
    target = normalize(target)
    if not source.is_file():
        raise ConversionError(tr('File non trovato o non regolare: {0}', source))
    family = family_for(source.suffix)
    if family is None or target not in targets_for(source, available_only=False):
        raise ConversionError(tr('Conversione {0} → {1} non supportata.', source.suffix, target))
    options.validate()
    source_stem = source.stem
    if family.name == "archive" and source.name.lower().endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
        source_stem = source.stem[:-4]
    stem = output_stem(source_stem, target, options.name_template)
    executable = None
    if family.engine != "pillow":
        executable = find_engine(family.engine)
        if not executable:
            raise ConversionError(tr('Motore mancante: {0}. Installalo e riavvia Muta.', family.engine))
    elif not image_supported(source.suffix.lstrip("."), target):
        raise ConversionError(tr("Codec immagine non disponibile. Per HEIC/HEIF installa l'extra heif."))
    directory = Path(output_dir).expanduser().resolve() if output_dir else source.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".muta-", dir=directory) as work:
            staged = Path(work) / f"converted.{target}"
            if family.engine == "pillow":
                convert_image(source, staged, target, options)
            elif family.engine == "libreoffice":
                convert_office(source, staged, target, family, executable, options)
            elif family.engine == "sevenzip":
                from .archives import convert_archive
                convert_archive(source, staged, target, executable, options)
            else:
                convert_media(source, staged, target, executable, options)
            if not staged.is_file() or staged.stat().st_size == 0:
                raise ConversionError(tr('Il motore non ha prodotto un file valido.'))
            return publish(staged, directory, stem, target)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(tr('Conversione non riuscita: {0}', exc)) from exc
