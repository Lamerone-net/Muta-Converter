from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from muta.engines import ConversionError
from muta.integration import menu_entries, not_mutable_condition
from muta.settings import Settings, clone_preset, load_settings, save_settings

TEMP_ROOT = Path(__file__).resolve().parents[1] / '.test-output'
TEMP_ROOT.mkdir(exist_ok=True)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=TEMP_ROOT)
        self.environment = patch.dict(os.environ, {'MUTA_CONFIG_DIR': self.folder.name})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.folder.cleanup()

    def test_settings_roundtrip(self):
        settings = Settings()
        settings.presets[0].name = 'Foto qualità alta'
        settings.presets[0].options = replace(settings.presets[0].options, quality=96)
        save_settings(settings)
        loaded = load_settings()
        self.assertEqual(loaded.presets[0].name, 'Foto qualità alta')
        self.assertEqual(loaded.presets[0].options.quality, 96)

    def test_legacy_names_migrate_without_changing_custom_names(self):
        settings = Settings()
        settings.preset('video_mkv').name = 'In MKV'
        settings.preset('presentation_ppt').name = 'My slides'
        save_settings(settings)
        loaded = load_settings()
        self.assertEqual(loaded.preset('video_mkv').name, 'MKV - Matroska')
        self.assertEqual(loaded.preset('presentation_ppt').name, 'My slides')

    def test_invalid_settings_not_silently_reset(self):
        path = Path(self.folder.name) / 'settings.json'
        path.write_text('{broken')
        with self.assertRaisesRegex(ConversionError, 'Preferenze non leggibili'):
            load_settings()
        self.assertEqual(path.read_text(), '{broken')

    def test_duplicate_and_disabled_presets(self):
        settings = Settings()
        copy = clone_preset(settings.presets[0])
        self.assertNotEqual(copy.id, settings.presets[0].id)
        copy.enabled = False
        settings.presets.append(copy)
        with self.assertRaises(ConversionError):
            settings.preset(copy.id)

    @patch('muta.integration.find_engine', return_value=None)
    def test_menu_filters_unavailable_families_and_presets(self, _):
        settings = Settings()
        preset = settings.presets[0]
        preset.inputs = ['webp']
        entries = menu_entries(settings)
        self.assertIn('webp', entries)
        self.assertNotIn('pages', entries)
        self.assertFalse(any(identifier == preset.id for identifier, _, _ in entries['png']))
        command = next(command for identifier, _, command in entries['webp'] if identifier == preset.id)
        self.assertIn('--preset image_jpg', command)
        self.assertTrue(command.endswith(' -- "%1"'))
        condition = not_mutable_condition(entries)
        self.assertIn('System.FileExtension:=.webp', condition)
        self.assertNotIn('.pages', condition)
        self.assertTrue(condition.startswith('NOT ('))

    def test_all_disabled_marks_every_file_not_mutable(self):
        settings = Settings()
        for preset in settings.presets:
            preset.enabled = False
        self.assertEqual(menu_entries(settings), {})
        self.assertEqual(not_mutable_condition({}), '')
