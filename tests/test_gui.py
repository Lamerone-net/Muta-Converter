import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent
from muta.gui import Preferences
from muta.settings import Settings, load_settings
from muta.updates import Release
from PySide6.QtWidgets import QMessageBox

TEMP_ROOT = Path(__file__).resolve().parents[1] / '.test-output'
TEMP_ROOT.mkdir(exist_ok=True)


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_edit_select_save_preset(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, patch.dict(os.environ, {'MUTA_CONFIG_DIR': folder}), \
                patch('muta.gui.set_autostart'), patch('muta.gui.menu_installed', return_value=False), \
                patch('muta.gui.QMessageBox.warning', side_effect=lambda *args: (_ for _ in ()).throw(AssertionError(args[-1]))):
            window = Preferences(Settings())
            window.fields['quality'].setValue(77)
            window.name.setText('Web quality')
            window.presets.setCurrentRow(1)
            self.assertEqual(window.settings.presets[0].options.quality, 77)
            self.assertTrue(window.save())
            self.assertEqual(load_settings().presets[0].name, 'Web quality')
            self.assertEqual(window.tabs.count(), 4)
            window.close()

    def test_every_preset_displays_and_duplicates(self):
        window = Preferences(Settings())
        for index in range(len(window.settings.presets)):
            window.presets.setCurrentRow(index)
            self.assertEqual(window.target.currentText(), window.settings.presets[index].target)
        old_count = len(window.settings.presets)
        window.duplicate_preset()
        self.assertEqual(len(window.settings.presets), old_count + 1)
        window.delete_preset()
        self.assertEqual(len(window.settings.presets), old_count)
        window.close()

    def test_update_download_and_install_require_separate_consent(self):
        release = Release('0.2.0', 'Changes', 'https://github.com/Lamerone-net/Muta-Converter/releases/tag/v0.2.0',
                          'https://github.com/Lamerone-net/Muta-Converter/releases/download/v0.2.0/setup.exe', '0' * 64, 100)
        window = Preferences(Settings())
        with patch('muta.gui.sys.platform', 'win32'), patch('muta.gui.QMessageBox.exec', return_value=QMessageBox.No), \
                patch.object(window, 'start_update_worker') as start:
            window.offer_update(release, False)
            start.assert_not_called()
        with patch('muta.gui.QMessageBox.question', return_value=QMessageBox.No), \
                patch('muta.gui.launch_installer') as launch:
            window.offer_install(Path('not-downloaded.exe'), release)
            launch.assert_not_called()
        self.assertFalse(window.settings.check_updates_on_start)
        window.close()
