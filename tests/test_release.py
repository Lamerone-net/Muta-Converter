import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('muta_release', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_current_version_has_release_notes(self):
        self.assertRegex(release.notes(release.current_version()), r'(?m)^### (Added|Changed|Fixed|Removed|Security)\s*$')

    def test_prepare_release_updates_version_and_moves_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src/muta').mkdir(parents=True)
            (root / 'src/muta/__init__.py').write_text('__version__ = "0.1.0"\n')
            (root / 'CHANGELOG.md').write_text('# Changelog\n\n## [Unreleased]\n\n### Fixed\n\n- Example fix.\n\n## [0.1.0] - 2026-11-24\n\n- Initial.\n')
            release.prepare('0.1.1', root)
            self.assertEqual(release.current_version(root), '0.1.1')
            self.assertIn('Example fix.', release.notes('0.1.1', root))
            self.assertNotIn('Example fix.', release.notes('0.1.0', root))
            with self.assertRaises(ValueError):
                release.prepare('0.1.2', root)
            with self.assertRaises(ValueError):
                release.prepare('0.0.9', root)
