import ast
from dataclasses import replace
import json
import os
from pathlib import Path
from string import Formatter
import tempfile
import unittest
from unittest.mock import Mock, patch

from muta.cli import main
from muta.i18n import LANGUAGES, INSTALLER_LANGUAGES, catalog, set_language, tr
from muta.integration import install_menu, PREFIX, FALLBACK_KEY
from muta.settings import Settings, load_settings, save_settings

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / '.test-output'
TEMP_ROOT.mkdir(exist_ok=True)


class Key:
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        set_language('it')

    def test_every_message_and_placeholder_is_present_in_every_language(self):
        source = catalog('it')
        def fields(text):
            return sorted((name, spec, conv) for _, name, spec, conv in Formatter().parse(text) if name is not None)
        for language in LANGUAGES:
            messages = catalog(language)
            self.assertEqual(set(messages), set(source))
            for key, text in messages.items():
                with self.subTest(language=language, key=key):
                    self.assertTrue(text.strip())
                    self.assertEqual(fields(key), fields(text))
        for path in (ROOT / 'src/muta').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr' and node.args and isinstance(node.args[0], ast.Constant):
                    self.assertIn(node.args[0].value, source, f'{path}:{node.lineno}')

    def test_installation_language_persists_before_refreshing_existing_menu(self):
        for installer_language, language in INSTALLER_LANGUAGES.items():
            with self.subTest(language=language), tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, \
                    patch.dict(os.environ, {'MUTA_CONFIG_DIR': folder}), \
                    patch('muta.integration.menu_installed', return_value=True), \
                    patch('muta.integration.install_menu') as refresh:
                settings = Settings(output_dir='custom-output')
                settings.presets[0].name = 'My photo preset'
                settings.presets[0].options = replace(settings.presets[0].options, quality=77)
                save_settings(settings)
                self.assertEqual(main(['configure', '--language', installer_language]), 0)
                loaded = load_settings()
                self.assertEqual(loaded.language, language)
                self.assertEqual(loaded.output_dir, 'custom-output')
                self.assertEqual(loaded.presets[0].name, 'My photo preset')
                self.assertEqual(loaded.presets[0].options.quality, 77)
                self.assertEqual(refresh.call_args.args[0].language, language)

    def test_actual_registry_values_use_installed_language_not_process_language(self):
        expected = {'en': 'Muta · Convert to', 'fr': 'Muta · Convertir en',
                    'de': 'Muta · Konvertieren in', 'es': 'Muta · Convertir a', 'it': 'Muta · Converti in'}
        for code, title in expected.items():
            with self.subTest(language=code):
                set_language('it')
                registry = Mock()
                registry.CreateKey.side_effect = lambda hive, path: Key(path)
                with patch('muta.integration._require_windows', return_value=registry), \
                        patch('muta.integration.remove_menu'), patch('muta.integration._notify_shell'):
                    install_menu(Settings(language=code))
                values = {(call.args[0].path, call.args[1]): call.args[4] for call in registry.SetValueEx.call_args_list}
                self.assertEqual(values[(PREFIX + r'\.webp\shell\MutaConverter', 'MUIVerb')], title)
                self.assertEqual(values[(FALLBACK_KEY, 'MUIVerb')], tr('Not mutable', language=code))
                self.assertEqual(values[(PREFIX + r'\.webp\shell\MutaConverter\shell\999_preferences', 'MUIVerb')], tr('Preferences…', language=code))

    def test_default_names_localize_but_custom_names_are_preserved(self):
        settings = Settings()
        preset = settings.preset('image_ico')
        self.assertEqual(preset.display_name('en'), 'ICO - Windows Icon')
        preset.name = 'ICO - Windows Icon'
        self.assertEqual(preset.display_name('de'), 'ICO - Windows-Symbol')
        preset.name = 'My icon'
        self.assertEqual(preset.display_name('fr'), 'My icon')

    def test_old_settings_keep_italian(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, patch.dict(os.environ, {'MUTA_CONFIG_DIR': folder}):
            save_settings(Settings())
            path = Path(folder) / 'settings.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            del data['language']
            path.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(load_settings().language, 'it')

    def test_installer_sets_language_before_registering_menu_and_starting_app(self):
        script = (ROOT / 'installer/windows.iss').read_text(encoding='utf-8')
        run = script.split('[Run]')[1].split('[UninstallRun]')[0]
        self.assertLess(run.index('configure --language {language}'), run.index('shell install'))
        self.assertLess(run.index('configure --language {language}'), run.index('--tray'))
        for language in ('english', 'french', 'german', 'spanish', 'italian'):
            self.assertIn(f'Name: "{language}";', script)
            self.assertIn(f'{language}.ContextMenu=', script)
