"""Adapters for Pillow, LibreOffice and FFmpeg. No command shell involved."""

from __future__ import annotations

import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageOps

from .catalog import Family

try:
    import pillow_heif
except ImportError:
    pillow_heif = None
else:
    pillow_heif.register_heif_opener()

Image.init()


class ConversionError(Exception):
    """An actionable conversion failure, safe to show to the user."""


def find_engine(name: str) -> str | None:
    variable = {"ffmpeg": "MUTA_FFMPEG", "libreoffice": "MUTA_LIBREOFFICE", "sevenzip": "MUTA_7ZIP"}[name]
    override = os.environ.get(variable)
    if override:
        return str(Path(override).resolve()) if Path(override).is_file() else None
    commands = {"ffmpeg": ("ffmpeg",), "libreoffice": ("soffice", "libreoffice"),
                "sevenzip": ("7zz", "7z", "7za")}[name]
    for command in commands:
        found = shutil.which(command)
        if found:
            return found
    if name == "libreoffice":
        candidates = [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            if os.environ.get(variable):
                candidates.append(Path(os.environ[variable]) / "LibreOffice/program/soffice.exe")
        return next((str(p) for p in candidates if p.is_file()), None)
    if name == "sevenzip":
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "7-Zip/7z.exe"
        return str(candidate) if candidate.is_file() else None
    return None


def diagnostics() -> dict[str, str | None]:
    from PIL import __version__
    return {"pillow": __version__, "libreoffice": find_engine("libreoffice"),
            "ffmpeg": find_engine("ffmpeg"),
            "7zip": find_engine("sevenzip"),
            "heif": "disponibile" if pillow_heif else None}


def image_supported(source_ext: str, target: str) -> bool:
    input_format = Image.registered_extensions().get("." + source_ext.lower())
    output_format = IMAGE_FORMATS[target]
    return input_format in Image.OPEN and output_format in Image.SAVE


IMAGE_FORMATS = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "avif": "AVIF",
                 "gif": "GIF", "bmp": "BMP", "tiff": "TIFF", "ico": "ICO", "pdf": "PDF"}


def convert_image(source: Path, destination: Path, target: str, settings) -> None:
    with Image.open(source) as original:
        if getattr(original, "n_frames", 1) > 1 and not settings.first_frame:
            raise ConversionError("Il file contiene più fotogrammi o pagine. Abilita esplicitamente "
                                  "'Solo prima pagina/fotogramma' oppure usa un altro convertitore.")
        frame = ImageOps.exif_transpose(original)
        if settings.scale != 100:
            frame = frame.resize((max(1, round(frame.width * settings.scale / 100)),
                                  max(1, round(frame.height * settings.scale / 100))), Image.Resampling.LANCZOS)
        if settings.rotation:
            frame = frame.rotate(-settings.rotation, expand=True)
        if target in {"jpg", "pdf", "bmp"}:
            rgba = frame.convert("RGBA")
            canvas = Image.new("RGB", rgba.size, settings.background)
            canvas.paste(rgba, mask=rgba.getchannel("A"))
            frame = canvas
        elif target == "gif":
            frame = frame.convert("RGBA")
        elif frame.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            frame = frame.convert("RGBA")
        if target == "ico":
            frame = frame.convert("RGBA")
            frame.thumbnail((256, 256), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (256, 256))
            canvas.paste(frame, ((256 - frame.width) // 2, (256 - frame.height) // 2))
            frame = canvas
        # Deliberately omit metadata; orientation has already been applied.
        frame.info.clear()
        options = {"quality": settings.quality} if target in {"jpg", "webp", "avif"} else {}
        frame.save(destination, format=IMAGE_FORMATS[target], **options)


OFFICE_FILTERS = {
    "document": {"doc": "MS Word 97", "docx": "Office Open XML Text", "odt": "writer8",
                 "rtf": "Rich Text Format", "txt": "Text (encoded):UTF8",
                 "pdf": "writer_pdf_Export", "epub": "EPUB"},
    "spreadsheet": {"xls": "MS Excel 97", "xlsx": "Calc MS Excel 2007 XML", "ods": "calc8",
                    "csv": "Text - txt - csv (StarCalc):44,34,76,1", "pdf": "calc_pdf_Export"},
    "presentation": {"ppt": "MS PowerPoint 97", "pptx": "Impress MS PowerPoint 2007 XML",
                     "odp": "impress8", "pdf": "impress_pdf_Export"},
}


def run_process(command: list[str], timeout: int, cwd: Path | None = None) -> str:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout,
                                creationflags=flags, check=False, cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(f"Tempo massimo superato ({timeout} secondi).") from exc
    except OSError as exc:
        raise ConversionError(f"Impossibile avviare il motore: {exc}") from exc
    if result.returncode:
        details = (result.stderr or result.stdout).strip()[-1800:]
        raise ConversionError(f"Il motore ha restituito un errore ({result.returncode}).\n{details}")
    return result.stdout


def convert_office(source: Path, destination: Path, target: str, family: Family,
                   executable: str, settings) -> None:
    # Separate profile also avoids forwarding to an already-open office session.
    with tempfile.TemporaryDirectory(prefix="muta-office-") as folder:
        root = Path(folder)
        out = root / "output"
        out.mkdir()
        output_filter = OFFICE_FILTERS[family.name][target]
        if target == "pdf":
            output_filter += ":" + json.dumps({
                "Quality": {"type": "long", "value": str(settings.pdf_quality)},
                "UseLosslessCompression": {"type": "boolean", "value": str(settings.pdf_lossless).lower()},
            })
        elif target == "csv":
            output_filter = f"Text - txt - csv (StarCalc):{ord(settings.csv_separator)},34,76,1"
        run_process([executable, f"-env:UserInstallation={(root / 'profile').as_uri()}",
                     "--headless", "--nologo", "--nodefault", "--norestore",
                     "--convert-to", f"{target}:{output_filter}",
                     "--outdir", str(out), str(source)], settings.timeout)
        converted = out / f"{source.stem}.{target}"
        if not converted.is_file() or converted.stat().st_size == 0:
            raise ConversionError("LibreOffice non ha prodotto un file. Il formato/versione del "
                                  "documento potrebbe non essere supportato, oppure il file è protetto.")
        shutil.copyfile(converted, destination)


AUDIO_ARGS = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "wav": ["-c:a", "pcm_s16le"], "flac": ["-c:a", "flac"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    "opus": ["-c:a", "libopus", "-b:a", "160k"], "aiff": ["-c:a", "pcm_s16be"],
}


def convert_media(source: Path, destination: Path, target: str, executable: str,
                  settings) -> None:
    args = [executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source)]
    if target in AUDIO_ARGS:
        args += ["-map", "0:a:0", "-vn", *AUDIO_ARGS[target]]
        if target in {"m4a", "opus"}:
            args += ["-b:a", f"{settings.audio_bitrate}k"]
    else:
        args += ["-map", "0:v:0", "-sn", "-dn"]
        args += ["-map", "0:a:0?"] if settings.include_audio else ["-an"]
        filters = []
        if settings.scale != 100:
            factor = settings.scale / 100
            filters.append(f"scale=max(2\\,trunc(iw*{factor}/2)*2):max(2\\,trunc(ih*{factor}/2)*2)")
        filters += {0: [], 90: ["transpose=1"], 180: ["hflip", "vflip"], 270: ["transpose=2"]}[settings.rotation]
        filters.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
        args += ["-vf", ",".join(filters), "-pix_fmt", "yuv420p"]
        if target == "webm":
            args += ["-c:v", "libvpx-vp9", "-crf", str(settings.video_crf), "-b:v", "0", "-c:a", "libopus"]
        else:
            args += ["-c:v", "libx264", "-crf", str(settings.video_crf), "-preset", settings.video_preset, "-c:a", "aac"]
            if target in {"mp4", "mov"}:
                args += ["-movflags", "+faststart"]
        if settings.include_audio:
            args += ["-b:a", f"{settings.audio_bitrate}k"]
    run_process([*args, str(destination)], settings.timeout)
