"""Render the actual Qt preferences without changing user configuration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from muta.gui import Preferences
from muta.settings import Settings

app = QApplication([])
if os.name == 'nt':
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QFont('Segoe UI', 10))
window = Preferences(Settings())
window.show()
app.processEvents()
output = Path(__file__).resolve().parents[1] / 'build/previews'
output.mkdir(parents=True, exist_ok=True)
window.grab().save(str(output / 'preferences.png'))
window.presets.setCurrentRow(next(i for i, p in enumerate(window.settings.presets) if p.id == 'video_mkv'))
app.processEvents()
window.grab().save(str(output / 'video.png'))
print(output)
window.close()
