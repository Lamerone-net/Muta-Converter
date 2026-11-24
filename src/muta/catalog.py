"""Explicit format families: never offer arbitrary cross-family conversion."""

from dataclasses import dataclass
from .i18n import tr


@dataclass(frozen=True)
class Family:
    name: str
    label: str
    engine: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


FAMILIES = (
    Family("image", "Immagini", "pillow",
           tuple("jpg jpeg png webp avif gif bmp tif tiff ico ppm pgm pbm tga pcx psd dds icns heic heif".split()),
           tuple("jpg png webp avif gif bmp tiff ico pdf".split())),
    Family("document", "Documenti", "libreoffice",
           tuple("doc docx odt ott rtf txt pages fodt wpd".split()),
           tuple("doc docx odt rtf txt pdf epub".split())),
    Family("spreadsheet", "Fogli di calcolo", "libreoffice",
           tuple("xls xlsx xlsm xlsb ods ots csv tsv numbers fods".split()),
           tuple("xls xlsx ods csv pdf".split())),
    Family("presentation", "Presentazioni", "libreoffice",
           tuple("ppt pptx pps ppsx odp otp key fodp".split()),
           tuple("ppt pptx odp pdf".split())),
    Family("audio", "Audio", "ffmpeg",
           tuple("mp3 wav flac aac m4a ogg opus aiff aif wma amr ape".split()),
           tuple("mp3 wav flac m4a ogg opus aiff".split())),
    Family("video", "Video", "ffmpeg",
           tuple("mp4 mkv mov avi webm m4v mpg mpeg wmv flv ts mts m2ts 3gp ogv".split()),
           tuple("mp4 mkv mov webm mp3 wav flac m4a ogg opus".split())),
    Family("archive", "Archivi", "sevenzip",
           tuple("zip 7z tar tgz gz tbz tbz2 bz2 txz xz arj rar cab lzh lha z".split()),
           tuple("zip 7z tar tgz tbz2 txz".split())),
)

ALIASES = {"jpeg": "jpg", "tif": "tiff"}
APPLE_INPUTS = {"pages", "numbers", "key"}

FORMAT_NAMES = {
    "jpg": "JPEG", "png": "Portable Network Graphics", "webp": "WebP",
    "avif": "AV1 Image File Format", "gif": "Graphics Interchange Format",
    "bmp": "Bitmap", "tiff": "Tagged Image File Format", "ico": "Icona Windows",
    "pdf": "Portable Document Format", "doc": "Word", "docx": "Word",
    "odt": "OpenDocument Text", "rtf": "Rich Text Format", "txt": "Testo semplice",
    "epub": "eBook", "xls": "Excel", "xlsx": "Excel", "ods": "OpenDocument Spreadsheet",
    "csv": "Comma-Separated Values", "ppt": "PowerPoint", "pptx": "PowerPoint",
    "odp": "OpenDocument Presentation", "mp3": "MPEG Audio Layer III", "wav": "Wave Audio",
    "flac": "Free Lossless Audio Codec", "m4a": "MPEG-4 Audio", "ogg": "Ogg Vorbis",
    "opus": "Opus Audio", "aiff": "Audio Interchange File Format", "mp4": "MPEG-4 Video",
    "mkv": "Matroska", "mov": "QuickTime", "webm": "WebM",
    "zip": "ZIP Archive", "7z": "7-Zip", "tar": "Tape Archive",
    "tgz": "TAR + Gzip", "tbz2": "TAR + Bzip2", "txz": "TAR + XZ",
}


def format_label(target: str, language: str = "it") -> str:
    return f"{target.upper()} - {tr(FORMAT_NAMES[target], language=language)}"


def normalize(extension: str) -> str:
    value = extension.lower().lstrip(".")
    return ALIASES.get(value, value)


def family_for(extension: str) -> Family | None:
    value = extension.lower().lstrip(".")
    return next((family for family in FAMILIES if value in family.inputs), None)
