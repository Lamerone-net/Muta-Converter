"""Qt preferences, tray application and responsive conversion progress."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import sys
import threading

from PySide6.QtCore import QLockFile, QThread, QTimer, Qt, Signal, QUrl
from PySide6.QtGui import QAction, QIcon, QDesktopServices
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QStyle, QSystemTrayIcon, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from . import __version__
from .catalog import FAMILIES, family_for
from .engines import ConversionError, diagnostics
from .integration import install_menu, menu_installed, remove_menu, set_autostart
from .service import Options, convert, targets_for
from .settings import Preset, Settings, clone_preset, config_dir, load_settings, save_settings
from .updates import check_latest, download_installer, launch_installer


class UpdateWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, release=None):
        super().__init__()
        self.release = release

    def run(self):
        try:
            result = download_installer(self.release, self.progress.emit) if self.release else check_latest(__version__)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


def app_icon() -> QIcon:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    logo = root / "assets/branding/logo.png"
    return QIcon(str(logo)) if logo.is_file() else QApplication.style().standardIcon(QStyle.SP_BrowserReload)


def about(parent=None):
    QMessageBox.about(parent, "About Muta Converter", f"<h3>Muta Converter {__version__}</h3>"
        "<p>Convert files, locally.</p><p>Python · Qt · Pillow · LibreOffice · FFmpeg</p>"
        '<p><a href="https://github.com/Lamerone-net/Muta-Converter">GitHub</a></p>'
        "<p>I file vengono elaborati sul computer. LibreOffice e FFmpeg sono motori esterni.</p>")


class ConversionWorker(QThread):
    result = Signal(str, bool)
    progress = Signal(int)

    def __init__(self, files, target, options, output_dir):
        super().__init__()
        self.files, self.target, self.options, self.output_dir = files, target, options, output_dir
        self.cancelled = threading.Event()
        self.failures = 0
        self.completed = 0

    def run(self):
        for index, source in enumerate(self.files):
            if self.cancelled.is_set():
                break
            try:
                output = convert(source, self.target, self.output_dir, self.options)
                self.result.emit(str(output), True)
            except Exception as exc:
                self.failures += 1
                self.result.emit(f"{source.name}: {exc}", False)
            self.completed += 1
            self.progress.emit(index + 1)


class ConversionDialog(QDialog):
    def __init__(self, files, target, options, output_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Muta · Conversione")
        self.setWindowIcon(app_icon())
        self.resize(680, 360)
        layout = QVBoxLayout(self)
        self.heading = QLabel(f"Conversione di {len(files)} file in {target.upper()}…")
        layout.addWidget(self.heading)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(files))
        layout.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        self.button = QPushButton("Interrompi dopo il file corrente")
        layout.addWidget(self.button)
        self.worker = ConversionWorker(files, target, options, output_dir)
        self.worker.result.connect(lambda text, ok: self.log.append(("OK · " if ok else "ERRORE · ") + text.replace("<", "&lt;")))
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.done_work)
        self.button.clicked.connect(self.stop_or_close)
        QTimer.singleShot(0, self.worker.start)

    def stop_or_close(self):
        if self.worker.isRunning():
            self.worker.cancelled.set()
            self.button.setText("Attendo il completamento del file corrente…")
            self.button.setEnabled(False)
        else:
            self.accept()

    def done_work(self):
        count, errors = self.worker.completed, self.worker.failures
        self.heading.setText(f"Terminato · {count - errors} riusciti · {errors} errori · "
                             f"{len(self.worker.files) - count} non elaborati")
        self.button.setText("Chiudi")
        self.button.setEnabled(True)

    def reject(self):
        if not self.worker.isRunning():
            super().reject()

    def closeEvent(self, event):
        if self.worker.isRunning():
            event.ignore()
        else:
            event.accept()


class Preferences(QDialog):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.current = None
        self.update_workers = []
        self.setWindowTitle("Muta Converter · Preferences")
        self.setWindowIcon(app_icon())
        self.resize(1000, 720)
        self.setMinimumSize(800, 560)
        outer = QVBoxLayout(self)
        title = QLabel("Muta Converter")
        title.setStyleSheet("font-size: 24px; font-weight: 600; margin: 8px 0;")
        outer.addWidget(title)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        self.make_presets_tab()
        self.make_application_tab()
        self.make_updates_tab()
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_layout.addWidget(QLabel(f"Muta Converter {__version__}\n\nConversioni locali · Windows, macOS, Linux"))
        about_layout.addWidget(QLabel("Apple iWork: Pages → documenti, Numbers → fogli, Keynote → presentazioni.\n"
            "L'importazione dipende dalla versione del file e da LibreOffice. Nessuna esportazione in iWork.\n\n"
            "Il menu contestuale è attualmente disponibile su Windows nel menu classico.\n"
            "Su Windows 11: Mostra altre opzioni.\n"
            "Selezione multipla: usa il pulsante Converti file.\n\n"
            "Le immagini vengono esportate senza metadati. CSV conserva un solo foglio;\n"
            "i video conservano la prima traccia video e, se richiesta, la prima traccia audio."))
        about_layout.addStretch()
        self.tabs.addTab(about_tab, "About")
        self.status = QLabel("Premi Salva per applicare le modifiche.")
        outer.addWidget(self.status)
        buttons = QHBoxLayout()
        convert_button = QPushButton("Converti file…")
        convert_button.clicked.connect(self.choose_conversion)
        buttons.addWidget(convert_button)
        buttons.addStretch()
        save = QPushButton("Salva")
        save.clicked.connect(self.save)
        close = QPushButton("Chiudi")
        close.clicked.connect(self.close)
        buttons.addWidget(close)
        buttons.addWidget(save)
        outer.addLayout(buttons)
        self.refresh_list()

    def make_updates_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel(f"Versione installata: {__version__}"))
        self.auto_updates = QCheckBox("Controlla nuove versioni all'avvio (solo controllo, nessun download automatico)")
        self.auto_updates.setChecked(self.settings.check_updates_on_start)
        layout.addWidget(self.auto_updates)
        self.check_button = QPushButton("Controlla aggiornamenti")
        self.check_button.clicked.connect(lambda: self.check_updates(False))
        layout.addWidget(self.check_button)
        self.update_status = QLabel("Gli aggiornamenti provengono dalle GitHub Releases ufficiali di Muta.")
        self.update_status.setWordWrap(True)
        layout.addWidget(self.update_status)
        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.hide()
        layout.addWidget(self.update_progress)
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setPlaceholderText("Il changelog della nuova versione apparirà qui.")
        layout.addWidget(self.release_notes)
        layout.addWidget(QLabel("Download e avvio dell'installer richiedono due conferme separate.\n"
                               "L'installer viene verificato tramite SHA-256. L'installazione guidata resta interattiva."))
        self.tabs.addTab(tab, "Updates")

    def start_update_worker(self, worker, callback):
        self.update_workers.append(worker)
        self.check_button.setEnabled(False)
        worker.succeeded.connect(callback)
        worker.failed.connect(self.update_failed)
        worker.progress.connect(self.update_progress.setValue)
        def finished():
            self.update_workers.remove(worker)
            self.check_button.setEnabled(not self.update_workers)
            worker.deleteLater()
        worker.finished.connect(finished)
        worker.start()

    def check_updates(self, quiet=False):
        if self.update_workers:
            return
        self.update_status.setText("Controllo delle release stabili su GitHub…")
        self.start_update_worker(UpdateWorker(), lambda release: self.offer_update(release, quiet))

    def update_failed(self, message):
        self.update_status.setText(message)
        self.update_progress.hide()

    def offer_update(self, release, quiet):
        if release is None:
            self.update_status.setText("Nessun aggiornamento disponibile.")
            return
        self.update_status.setText(f"Disponibile Muta Converter {release.version}.")
        self.release_notes.setPlainText(release.notes)
        self.showNormal()
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.release_notes.parentWidget()))
        if sys.platform != 'win32' or not release.installer_url:
            answer = QMessageBox.question(self, "Aggiornamento disponibile", "Aprire la pagina ufficiale per scaricare la nuova versione?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl(release.page_url))
            return
        question = QMessageBox(self)
        question.setWindowTitle("Aggiornamento disponibile")
        question.setText(f"Muta Converter {release.version} è disponibile.\nScaricare l'installer ({release.size / 1024 / 1024:.1f} MiB)?")
        question.setDetailedText(release.notes)
        question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        question.setDefaultButton(QMessageBox.No)
        if question.exec() == QMessageBox.Yes:
            self.update_status.setText("Download e verifica SHA-256…")
            self.update_progress.setValue(0)
            self.update_progress.show()
            self.start_update_worker(UpdateWorker(release), lambda path: self.offer_install(path, release))

    def offer_install(self, path, release):
        self.update_progress.hide()
        self.update_status.setText(f"Installer {release.version} scaricato e verificato.")
        if any(isinstance(widget, ConversionDialog) and widget.worker.isRunning()
               for widget in QApplication.topLevelWidgets()):
            QMessageBox.information(self, "Aggiornamento pronto", "Termina le conversioni prima di installare. Puoi ripetere il controllo aggiornamenti in seguito.")
            return
        answer = QMessageBox.question(self, "Installa aggiornamento", "Avviare l'installer adesso?\nWindows richiederà l'autorizzazione amministratore.\nMuta verrà chiuso; l'installazione guidata chiederà come procedere.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            try:
                launch_installer(path, release)
                # Wait for the download worker's finished signal before exiting Qt.
                QTimer.singleShot(200, self.quit_after_update)
            except (OSError, ConversionError) as exc:
                self.update_failed(str(exc))

    def quit_after_update(self):
        if self.update_workers:
            QTimer.singleShot(100, self.quit_after_update)
        else:
            QApplication.quit()

    def closeEvent(self, event):
        if any(worker.isRunning() for worker in self.update_workers):
            self.update_status.setText("Attendi il completamento del controllo o download in corso.")
            event.ignore()
        else:
            event.accept()

    def make_presets_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        splitter = QSplitter()
        layout.addWidget(splitter)
        left = QWidget()
        left.setMaximumWidth(310)
        left_layout = QVBoxLayout(left)
        self.presets = QListWidget()
        self.presets.currentRowChanged.connect(self.select_preset)
        left_layout.addWidget(self.presets)
        actions = QHBoxLayout()
        for title, callback in (("+", self.add_preset), ("Duplica", self.duplicate_preset),
                                ("−", self.delete_preset), ("↑", lambda: self.move_preset(-1)),
                                ("↓", lambda: self.move_preset(1))):
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        left_layout.addLayout(actions)
        splitter.addWidget(left)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        self.form = QFormLayout(form_widget)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.name = QLineEdit()
        self.enabled = QCheckBox("Mostra nel menu contestuale")
        self.target = QComboBox()
        self.target.currentTextChanged.connect(self.update_fields)
        self.inputs = QListWidget()
        self.inputs.setMaximumHeight(110)
        self.form.addRow("Nome preset", self.name)
        self.form.addRow("", self.enabled)
        self.form.addRow("Formato di uscita", self.target)
        self.form.addRow("Formati di ingresso", self.inputs)
        self.fields = {}
        specifications = [
            ("quality", "Qualità immagine (JPG/WebP/AVIF)", 1, 100),
            ("scale", "Dimensioni (%)", 1, 200),
            ("video_crf", "Qualità video CRF (minore = migliore)", 0, 51),
            ("audio_bitrate", "Bitrate AAC/Opus (kbps)", 32, 320),
            ("pdf_quality", "Qualità immagini PDF", 1, 100),
            ("timeout", "Timeout motore esterno (secondi)", 1, 86400),
            ("archive_level", "Livello compressione (0–9)", 0, 9),
            ("archive_limit_mb", "Limite estrazione (MiB)", 1, 1048576),
            ("archive_max_files", "Limite elementi nell'archivio", 1, 1000000),
        ]
        for key, label, low, high in specifications:
            widget = QSpinBox()
            widget.setRange(low, high)
            self.fields[key] = widget
            self.form.addRow(label, widget)
        for key, label, choices in (
            ("rotation", "Rotazione oraria", ["0", "90", "180", "270"]),
            ("video_preset", "Velocità encoder H.264", ["ultrafast", "fast", "medium", "slow", "veryslow"]),
            ("csv_separator", "Separatore CSV", [",", ";", "Tab"]),
        ):
            widget = QComboBox()
            widget.addItems(choices)
            self.fields[key] = widget
            self.form.addRow(label, widget)
        for key, label in (("background", "Sfondo per formati senza trasparenza"),
                            ("name_template", "Nome file: {name}, {format}")):
            widget = QLineEdit()
            self.fields[key] = widget
            self.form.addRow(label, widget)
        for key, label in (("first_frame", "Solo prima pagina/fotogramma (scarta gli altri)"),
                            ("include_audio", "Includi la prima traccia audio"),
                            ("pdf_lossless", "Immagini PDF senza perdita")):
            widget = QCheckBox(label)
            self.fields[key] = widget
            self.form.addRow(widget)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.form.addRow(self.note)
        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        splitter.setSizes([280, 650])
        self.tabs.addTab(tab, "Conversion Presets")

    def make_application_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.app_fields = {}
        for key, label in (("output_dir", "Cartella output (vuota = accanto all'originale)"),
                            ("libreoffice", "LibreOffice (vuoto = rilevamento automatico)"),
                            ("ffmpeg", "FFmpeg (vuoto = rilevamento automatico)"),
                            ("sevenzip", "7-Zip (vuoto = rilevamento automatico)")):
            row = QWidget()
            box = QHBoxLayout(row)
            box.setContentsMargins(0, 0, 0, 0)
            field = QLineEdit(getattr(self.settings, key))
            self.app_fields[key] = field
            button = QPushButton("Sfoglia…")
            button.clicked.connect(lambda checked=False, key=key: self.browse_path(key))
            box.addWidget(field)
            box.addWidget(button)
            layout.addRow(label, row)
        self.autostart = QCheckBox("Avvia Muta nella systray all'accesso a Windows")
        self.autostart.setChecked(self.settings.autostart)
        self.autostart.setEnabled(os.name == "nt")
        layout.addRow(self.autostart)
        menu_buttons = QWidget()
        buttons = QHBoxLayout(menu_buttons)
        for label, callback in (("Installa / aggiorna menu", self.install_shell), ("Rimuovi menu", self.remove_shell)):
            button = QPushButton(label)
            button.setEnabled(os.name == "nt")
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addRow("Esplora file", menu_buttons)
        self.engine_status = QLabel()
        self.engine_status.setWordWrap(True)
        layout.addRow("Motori rilevati", self.engine_status)
        refresh = QPushButton("Ricontrolla motori")
        refresh.clicked.connect(self.refresh_engines)
        layout.addRow(refresh)
        info = QLabel("Gli originali non vengono sovrascritti. I nomi già esistenti ricevono un numero.\n"
                      "HEIC/HEIF richiede pillow-heif. I codec audio/video dipendono dalla build FFmpeg.\n"
                      "Installa LibreOffice per abilitare i documenti, inclusa l'importazione iWork.\n"
                      "Installa 7-Zip per ZIP, TGZ, 7Z e altri archivi; ARJ/RAR sono solo in ingresso.\n"
                      "Dopo l'installazione di un motore, aggiorna il menu contestuale.\n"
                      "Not mutable indica l'assenza di preset disponibili; il menu Windows usa lo stile standard.")
        info.setWordWrap(True)
        layout.addRow(info)
        self.tabs.addTab(tab, "Application")
        self.refresh_engines()

    def refresh_list(self, index=0):
        self.current = None
        self.presets.blockSignals(True)
        self.presets.clear()
        for preset in self.settings.presets:
            family = next(f for f in FAMILIES if f.name == preset.family)
            self.presets.addItem(f"{preset.name}  ·  {family.label}")
        self.presets.blockSignals(False)
        if self.settings.presets:
            self.presets.setCurrentRow(min(index, len(self.settings.presets) - 1))

    def store_current(self):
        if self.current is None:
            return
        preset = self.settings.presets[self.current]
        preset.name = self.name.text()
        preset.enabled = self.enabled.isChecked()
        preset.target = self.target.currentText()
        preset.inputs = [self.inputs.item(i).text() for i in range(self.inputs.count())
                         if self.inputs.item(i).checkState() == Qt.Checked]
        values = {}
        for key, widget in self.fields.items():
            if isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
                if key == "rotation":
                    value = int(value)
                elif key == "csv_separator" and value == "Tab":
                    value = "\t"
            else:
                value = widget.text()
            values[key] = value
        preset.options = Options(**values)

    def select_preset(self, index):
        self.store_current()
        if index < 0:
            return
        self.current = index
        preset = self.settings.presets[index]
        family = next(f for f in FAMILIES if f.name == preset.family)
        self.name.setText(preset.name)
        self.enabled.setChecked(preset.enabled)
        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItems(family.outputs)
        self.target.setCurrentText(preset.target)
        self.target.blockSignals(False)
        self.inputs.clear()
        for extension in family.inputs:
            item = QListWidgetItem(extension)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if extension in preset.inputs else Qt.Unchecked)
            self.inputs.addItem(item)
        for key, value in asdict(preset.options).items():
            widget = self.fields[key]
            if isinstance(widget, QSpinBox):
                widget.setValue(value)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox):
                widget.setCurrentText("Tab" if value == "\t" else str(value))
            else:
                widget.setText(value)
        self.update_fields()

    def update_fields(self):
        if self.current is None:
            return
        family = self.settings.presets[self.current].family
        target = self.target.currentText()
        video = family == "video" and target in {"mp4", "mkv", "mov", "webm"}
        visible = {"name_template"}
        if family == "image":
            visible |= {"scale", "rotation", "first_frame"}
            if target in {"jpg", "webp", "avif"}:
                visible.add("quality")
            if target in {"jpg", "pdf", "bmp"}:
                visible.add("background")
        else:
            visible.add("timeout")
        if video:
            visible |= {"scale", "rotation", "video_crf", "include_audio", "audio_bitrate"}
            if target != "webm":
                visible.add("video_preset")
        if family in {"audio", "video"} and target in {"m4a", "opus"}:
            visible.add("audio_bitrate")
        if family in {"document", "spreadsheet", "presentation"} and target == "pdf":
            visible |= {"pdf_quality", "pdf_lossless"}
        if target == "csv":
            visible.add("csv_separator")
        if family == "archive":
            visible |= {"archive_limit_mb", "archive_max_files"}
            if target != "tar":
                visible.add("archive_level")
        for key, widget in self.fields.items():
            self.form.setRowVisible(widget, key in visible)
        notes = {"image": "L'orientamento EXIF viene applicato; i metadati vengono rimossi. Le animazioni e le immagini multipagina richiedono la scelta esplicita del primo fotogramma.",
                 "document": "Pages → DOC/DOCX/ODT/PDF. Compatibilità e impaginazione dipendono dal file e da LibreOffice.",
                 "spreadsheet": "Numbers → XLS/XLSX/ODS/PDF. CSV esporta un solo foglio e perde formattazione e formule.",
                 "presentation": "Keynote → PPT/PPTX/ODP/PDF. Alcune versioni di Keynote non sono importabili da LibreOffice.",
                 "audio": "MP3 usa qualità VBR 2; OGG qualità 5. WAV/AIFF: PCM 16 bit. FLAC: senza perdita.",
                 "video": "Si convertono la prima traccia video e la prima audio. Sottotitoli e altre tracce non vengono trasferiti.",
                 "archive": "Si estraggono i file e si crea un nuovo archivio. ARJ/RAR: solo lettura. Password, link, file speciali e percorsi non sicuri sono rifiutati. Permessi e metadati possono cambiare."}
        self.note.setText(notes[family])

    def add_preset(self):
        self.store_current()
        name, ok = QInputDialog.getItem(self, "Nuovo preset", "Tipo di conversione", [f.label for f in FAMILIES], 0, False)
        if ok:
            family = next(f for f in FAMILIES if f.label == name)
            import uuid
            self.settings.presets.append(Preset(uuid.uuid4().hex, "Nuovo preset", family.name, family.outputs[0], list(family.inputs)))
            self.refresh_list(len(self.settings.presets) - 1)

    def duplicate_preset(self):
        self.store_current()
        if self.current is not None:
            self.settings.presets.append(clone_preset(self.settings.presets[self.current]))
            self.refresh_list(len(self.settings.presets) - 1)

    def delete_preset(self):
        if self.current is not None and len(self.settings.presets) > 1:
            index = self.current
            self.settings.presets.pop(index)
            self.refresh_list(max(0, index - 1))

    def move_preset(self, direction):
        self.store_current()
        index = self.current
        if index is not None and 0 <= index + direction < len(self.settings.presets):
            presets = self.settings.presets
            presets[index], presets[index + direction] = presets[index + direction], presets[index]
            self.refresh_list(index + direction)

    def browse_path(self, key):
        path = QFileDialog.getExistingDirectory(self, "Cartella di destinazione") if key == "output_dir" else QFileDialog.getOpenFileName(self, "Seleziona eseguibile")[0]
        if path:
            self.app_fields[key].setText(path)

    def refresh_engines(self):
        self.settings.apply_engines()
        self.engine_status.setText("\n".join(f"{key}: {value or 'non disponibile'}" for key, value in diagnostics().items()))

    def save(self):
        try:
            self.store_current()
            for key, field in self.app_fields.items():
                value = field.text().strip()
                if key != "output_dir" and value and not Path(value).is_file():
                    raise ConversionError(f"Eseguibile non trovato: {value}")
                setattr(self.settings, key, value)
            self.settings.autostart = self.autostart.isChecked()
            self.settings.check_updates_on_start = self.auto_updates.isChecked()
            save_settings(self.settings)
            self.settings.apply_engines()
            if os.name == "nt":
                set_autostart(self.settings.autostart)
                if menu_installed():
                    install_menu(self.settings)
            self.refresh_engines()
            self.status.setText("Preferenze salvate.")
            self.refresh_list(self.current or 0)
            return True
        except (OSError, ConversionError) as exc:
            QMessageBox.warning(self, "Preferenze", str(exc))
            return False

    def install_shell(self):
        if self.save():
            try:
                install_menu(self.settings)
                self.status.setText("Menu contestuale aggiornato. Windows 11: Mostra altre opzioni.")
            except (OSError, ConversionError) as exc:
                QMessageBox.warning(self, "Menu contestuale", str(exc))

    def remove_shell(self):
        try:
            remove_menu()
            self.status.setText("Menu contestuale rimosso.")
        except OSError as exc:
            QMessageBox.warning(self, "Menu contestuale", str(exc))

    def choose_conversion(self):
        if not self.save():
            return
        names, _ = QFileDialog.getOpenFileNames(self, "Seleziona file da convertire")
        files = [Path(name) for name in names]
        if not files:
            return
        presets = [p for p in self.settings.presets if p.enabled and all(
            f.suffix.lower().lstrip(".") in p.inputs and p.target in targets_for(f) for f in files)]
        if not presets:
            QMessageBox.information(self, "Not mutable", "Nessun preset disponibile per tutti i file selezionati. Controlla i motori in Application.")
            return
        labels = [f"{i + 1}. {p.name} ({p.target.upper()})" for i, p in enumerate(presets)]
        label, ok = QInputDialog.getItem(self, "Converti in", "Preset", labels, 0, False)
        if ok:
            preset = presets[labels.index(label)]
            output = Path(self.settings.output_dir) if self.settings.output_dir else None
            dialog = ConversionDialog(files, preset.target, preset.options, output, self)
            dialog.exec()


def run_conversion(files, target, options, output_dir) -> int:
    app = QApplication.instance() or QApplication([])
    dialog = ConversionDialog(files, target, options, output_dir)
    dialog.exec()
    return 1 if dialog.worker.failures or dialog.worker.completed != len(files) else 0


def main(show_preferences=True) -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Muta Converter")
    app.setWindowIcon(app_icon())
    folder = config_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = "muta-" + hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:20]
    lock = QLockFile(str(folder / "tray.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(1000):
            socket.write(b"preferences" if show_preferences else b"tray")
            socket.waitForBytesWritten(1000)
        return 0
    try:
        settings = load_settings()
        settings.apply_engines()
        window = Preferences(settings)
        tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        app.setQuitOnLastWindowClosed(not tray_available)
        tray = QSystemTrayIcon(app_icon(), app)
        tray.setToolTip("Muta Converter")
        menu = QMenu()
        def show():
            window.showNormal()
            window.raise_()
            window.activateWindow()
        menu.addAction("Preferences", show)
        menu.addAction("About", lambda: about(window))
        menu.addSeparator()
        def quit_app():
            if window.update_workers:
                QMessageBox.information(window, "Muta", "Attendi il completamento del controllo o download in corso.")
                return
            if any(isinstance(widget, ConversionDialog) and widget.worker.isRunning()
                   for widget in app.topLevelWidgets()):
                QMessageBox.information(window, "Muta", "Attendi la conversione in corso oppure interrompi la coda dalla finestra di avanzamento.")
                return
            app.quit()
        menu.addAction("Quit", quit_app)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: show() if reason == QSystemTrayIcon.DoubleClick else None)
        tray.show()
        server = QLocalServer(app)
        QLocalServer.removeServer(name)
        server.listen(name)
        def connected():
            socket = server.nextPendingConnection()
            def read():
                if bytes(socket.readAll()) == b"preferences":
                    show()
                socket.disconnectFromServer()
                socket.deleteLater()
            socket.readyRead.connect(read)
            if socket.bytesAvailable():
                read()
        server.newConnection.connect(connected)
        if show_preferences or not tray_available:
            show()
        if settings.check_updates_on_start:
            QTimer.singleShot(1500, lambda: window.check_updates(True))
        result = app.exec()
        tray.hide()
        server.close()
        return result
    finally:
        lock.unlock()
