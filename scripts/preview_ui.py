"""Render the actual Qt preferences without changing user configuration."""
import os
import argparse
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from muta.gui import Preferences
from muta.settings import Settings
from muta.i18n import LANGUAGES
from PySide6.QtCore import QCoreApplication, QEvent

app = QApplication([])
if os.name == 'nt':
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QFont('Segoe UI', 10))
parser = argparse.ArgumentParser()
parser.add_argument('--language', choices=LANGUAGES, default='it')
parser.add_argument('--all', action='store_true')
args = parser.parse_args()
output = Path(__file__).resolve().parents[1] / 'build/previews'
output.mkdir(parents=True, exist_ok=True)
for language in LANGUAGES if args.all else [args.language]:
    window = Preferences(Settings(language=language))
    window.show()
    app.processEvents()
    suffix = '-' + language if args.all else ''
    window.grab().save(str(output / f'preferences{suffix}.png'))
    window.presets.setCurrentRow(next(i for i, p in enumerate(window.settings.presets) if p.id == 'video_mkv'))
    app.processEvents()
    window.grab().save(str(output / f'video{suffix}.png'))
    window.tabs.setCurrentIndex(1)
    app.processEvents()
    window.grab().save(str(output / f'application{suffix}.png'))
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
print(output)
