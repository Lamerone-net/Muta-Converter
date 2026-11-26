"""Per-conversion SVG raster settings; choices do not modify saved presets."""

from dataclasses import replace
import math
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
                              QLabel, QMessageBox, QSpinBox, QVBoxLayout)

from .catalog import normalize
from .engines import ConversionError, IMAGE_FORMATS
from .i18n import tr
from .resources import icon_path
from .svg import MAX_RENDER_PIXELS, load_renderer, output_dimensions

DPI_FORMATS = {"png", "jpg", "tiff", "bmp", "pdf"}


class SvgRasterDialog(QDialog):
    def __init__(self, source, target, options, parent=None):
        super().__init__(parent)
        self.source, self.target, self.options = Path(source), normalize(target), options
        self.setWindowTitle(tr('SVG → bitmap'))
        self.setWindowIcon(QIcon(str(icon_path())))
        self.setMinimumWidth(450)
        renderer, self.natural = load_renderer(self.source, options)
        natural_width, natural_height = self.natural
        if options.rotation in (90, 270):
            natural_width, natural_height = natural_height, natural_width
        self.ratio = natural_width / natural_height
        try:
            width, height = output_dimensions(self.natural, options)
        except ConversionError:
            factor = min(16384 / natural_width, 16384 / natural_height,
                         math.sqrt(MAX_RENDER_PIXELS / (natural_width * natural_height)))
            width, height = max(1, int(natural_width * factor)), max(1, int(natural_height * factor))
        layout = QVBoxLayout(self)
        filename = QLabel(tr('{0} → {1}', self.source.name, self.target.upper()))
        filename.setWordWrap(True)
        layout.addWidget(filename)
        form = QFormLayout()
        layout.addLayout(form)
        self.width_choice = QSpinBox()
        self.height_choice = QSpinBox()
        for widget, value in ((self.width_choice, width), (self.height_choice, height)):
            widget.setRange(1, 16384)
            widget.setValue(value)
            widget.setSuffix(' px')
        form.addRow(tr('Larghezza'), self.width_choice)
        form.addRow(tr('Altezza'), self.height_choice)
        self.lock_ratio = QCheckBox(tr('Mantieni proporzioni'))
        self.lock_ratio.setChecked(True)
        form.addRow(self.lock_ratio)
        self.dpi_choice = QSpinBox()
        self.dpi_choice.setRange(1, 2400)
        self.dpi_choice.setValue(options.svg_dpi)
        self.dpi_choice.setSuffix(' DPI')
        self.dpi_choice.setEnabled(self.target in DPI_FORMATS)
        form.addRow(tr('Risoluzione di stampa'), self.dpi_choice)
        if self.target == 'ico':
            for widget in (self.width_choice, self.height_choice):
                widget.setValue(256)
                widget.setEnabled(False)
            self.lock_ratio.setEnabled(False)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        note = QLabel(tr('I DPI definiscono la dimensione di stampa, non il numero di pixel. Le scelte valgono solo per questa conversione.'))
        if self.target not in DPI_FORMATS:
            note.setText(tr('Questo formato non salva i DPI. Le scelte valgono solo per questa conversione.'))
        if self.target == 'ico':
            note.setText(tr('ICO usa una tela di 256 × 256 pixel; il disegno mantiene le proporzioni.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr('Converti'))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.width_choice.valueChanged.connect(lambda: self.size_changed(True))
        self.height_choice.valueChanged.connect(lambda: self.size_changed(False))
        self.lock_ratio.toggled.connect(lambda checked: self.size_changed(True) if checked else None)
        self.dpi_choice.valueChanged.connect(self.refresh_summary)
        self.refresh_summary()

    def size_changed(self, width_changed):
        if self.lock_ratio.isChecked():
            if width_changed:
                width = self.width_choice.value()
                height = max(1, round(width / self.ratio))
                if height > 16384:
                    height, width = 16384, max(1, round(16384 * self.ratio))
            else:
                height = self.height_choice.value()
                width = max(1, round(height * self.ratio))
                if width > 16384:
                    width, height = 16384, max(1, round(16384 / self.ratio))
            for widget, value in ((self.width_choice, width), (self.height_choice, height)):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
        self.refresh_summary()

    def selected_options(self):
        width, height = self.width_choice.value(), self.height_choice.value()
        if self.target == 'ico':
            width, height = ((256, max(1, round(256 / self.ratio))) if self.ratio >= 1
                             else (max(1, round(256 * self.ratio)), 256))
        return replace(self.options, svg_width=width, svg_height=height, svg_dpi=self.dpi_choice.value())

    def refresh_summary(self):
        width, height, dpi = self.width_choice.value(), self.height_choice.value(), self.dpi_choice.value()
        valid = width * height <= MAX_RENDER_PIXELS
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(valid)
        if not valid:
            self.summary.setText(tr('Massimo 40 milioni di pixel. Riduci larghezza o altezza.'))
        elif self.target in DPI_FORMATS:
            self.summary.setText(tr('{0} × {1} pixel · stampa: {2:.1f} × {3:.1f} cm',
                                    width, height, width / dpi * 2.54, height / dpi * 2.54))
        else:
            self.summary.setText(tr('{0} × {1} pixel', width, height))


def prepare_svg_options(files, target, options, parent=None):
    choices = {}
    if normalize(target) not in IMAGE_FORMATS:
        return choices
    for source in files:
        if source.suffix.lower() != '.svg':
            continue
        try:
            dialog = SvgRasterDialog(source, target, options, parent)
            if dialog.exec() != QDialog.Accepted:
                return None
            choices[source] = dialog.selected_options()
        except Exception as exc:
            QMessageBox.warning(parent, tr('SVG → bitmap'), str(exc))
            return False
    return choices
