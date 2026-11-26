"""SVG rendering and tracing in a bounded child process, without external resources."""

from dataclasses import asdict, replace
import json
import math
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import fromstring
from PIL import Image

from .engines import ConversionError, convert_image, run_process
from .i18n import get_language, set_language, tr

MAX_SVG_BYTES = 32 * 1024 * 1024
MAX_RENDER_PIXELS = 40_000_000
MAX_TRACE_PIXELS = 4_000_000
SVG_NS = "http://www.w3.org/2000/svg"


def convert_svg(source, destination, target, settings):
    # The caller owns this temporary directory; failures are never published.
    job = destination.parent / "svg-job.json"
    error = destination.parent / "svg-error.txt"
    job.write_text(json.dumps({"source": str(source), "destination": str(destination),
                              "target": target, "options": asdict(settings),
                              "language": get_language()}), encoding="utf-8")
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).with_name("muta-cli.exe" if os.name == "nt" else "muta-cli")
        command = [str(executable)]
    else:
        command = [sys.executable, "-m", "muta"]
    try:
        run_process([*command, "_svg-worker", str(job)], settings.timeout)
    except ConversionError:
        if error.is_file():
            raise ConversionError(error.read_text(encoding="utf-8")) from None
        raise


def validated_svg(source, first_frame):
    with source.open("rb") as stream:
        data = stream.read(MAX_SVG_BYTES + 1)
    if len(data) > MAX_SVG_BYTES:
        raise ConversionError(tr("SVG troppo grande: massimo 32 MiB."))
    root = fromstring(data, forbid_entities=True, forbid_external=True)
    if root.tag not in ("svg", f"{{{SVG_NS}}}svg"):
        raise ConversionError(tr("File SVG non valido."))
    animation = False
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1]
        if name in {"script", "foreignObject"}:
            raise ConversionError(tr("SVG con script o contenuto HTML non supportato."))
        animation |= name in {"animate", "animateMotion", "animateTransform", "set"}
        for attribute, value in element.attrib.items():
            key = attribute.rsplit("}", 1)[-1]
            if key in {"href", "src", "base"}:
                if not (value.startswith("#") or re.fullmatch(
                        r"data:image/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=\s]+", value)):
                    raise ConversionError(tr("SVG con risorse esterne non supportato. Incorpora le immagini nel file."))
        styles = [element.attrib.get("style", "")]
        if name == "style":
            styles.append(element.text or "")
        for style in [*styles, *element.attrib.values()]:
            if "@import" in style.lower() or "\\" in style:
                raise ConversionError(tr("SVG con risorse esterne non supportato. Incorpora le immagini nel file."))
            for reference in re.findall(r"url\s*\((.*?)\)", style, re.I | re.S):
                if not reference.strip(" \t\r\n\"'").startswith("#"):
                    raise ConversionError(tr("SVG con risorse esterne non supportato. Incorpora le immagini nel file."))
        animation |= any(re.search(r"animation|@keyframes", style, re.I) for style in styles)
    if animation and not first_frame:
        raise ConversionError(tr("SVG animato: abilita 'Solo prima pagina/fotogramma' per esportare un'immagine statica."))
    # Re-serialization omits DTDs, processing instructions and entity declarations.
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    return ET.tostring(root, encoding="utf-8")


def render_svg(source, destination, settings):
    data = validated_svg(source, settings.first_frame)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer, QtSvg
    app = QGuiApplication([])
    if os.name == "nt":
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))
            app.setFont(QFont("Segoe UI", 10))
    renderer = QSvgRenderer()
    renderer.setOptions(QtSvg.Option.DisableSMILAnimations | QtSvg.Option.DisableCSSAnimations)
    if not renderer.load(QByteArray(data)) or not renderer.isValid():
        raise ConversionError(tr("File SVG non valido."))
    renderer.setAnimationEnabled(False)
    size = renderer.defaultSize()
    width, height = size.width(), size.height()
    if width <= 0 or height <= 0:
        box = renderer.viewBoxF()
        width, height = box.width(), box.height()
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ConversionError(tr("Dimensioni SVG mancanti o non valide."))
    width, height = max(1, round(width * settings.scale / 100)), max(1, round(height * settings.scale / 100))
    if max(width, height) > 16384 or width * height > MAX_RENDER_PIXELS:
        raise ConversionError(tr("SVG troppo grande da renderizzare. Riduci le dimensioni nel preset."))
    image = QImage(width, height, QImage.Format_RGBA8888)
    if image.isNull():
        raise ConversionError(tr("SVG troppo grande da renderizzare. Riduci le dimensioni nel preset."))
    image.fill(Qt.transparent)
    painter = QPainter(image)
    try:
        renderer.render(painter, QRectF(0, 0, width, height))
    finally:
        painter.end()
    if not image.save(str(destination), "PNG"):
        raise ConversionError(tr("Il motore non ha prodotto un file valido."))


def trace_image(source, destination, settings):
    import vtracer
    with Image.open(source) as original:
        scaled_pixels = max(1, round(original.width * settings.scale / 100)) * max(1, round(original.height * settings.scale / 100))
        if scaled_pixels > MAX_TRACE_PIXELS:
            raise ConversionError(tr("Immagine troppo grande da vettorializzare: massimo 4 milioni di pixel. Riduci le dimensioni nel preset."))
    raster = destination.parent / "trace.png"
    convert_image(source, raster, "png", settings)
    with Image.open(raster) as image:
        rgba = image.convert("RGBA")
    # Preserve fully transparent pixels, blend partial alpha with the chosen background.
    alpha = rgba.getchannel("A")
    background = Image.new("RGBA", rgba.size, settings.background)
    background.alpha_composite(rgba)
    background.putalpha(alpha.point(lambda a: 255 if a else 0))
    background.save(raster)
    vtracer.convert_image_to_svg_py(str(raster), str(destination),
        colormode="binary" if settings.svg_monochrome else "color",
        hierarchical="stacked", mode="spline", filter_speckle=settings.svg_speckle,
        color_precision=settings.svg_color_precision, path_precision=3)


def worker(job_path):
    from .service import Options
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        set_language(job["language"])
        settings = Options(**job["options"])
        settings.validate()
        source, destination = Path(job["source"]), Path(job["destination"])
        if job["target"] == "svg":
            trace_image(source, destination, settings)
        else:
            raster = destination.parent / "render.png"
            render_svg(source, raster, settings)
            convert_image(raster, destination, job["target"], replace(settings, scale=100))
        return 0
    except Exception as exc:
        (job_path.parent / "svg-error.txt").write_text(str(exc), encoding="utf-8")
        return 1
