from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from muta.engines import ConversionError
from muta.updates import Release, WEB_URL, download_installer, launch_installer, parse_release

TEMP_ROOT = Path(__file__).resolve().parents[1] / '.test-output'
TEMP_ROOT.mkdir(exist_ok=True)


class UpdateTests(unittest.TestCase):
    def release_data(self, version='0.2.0', payload=b'installer test bytes'):
        filename = f'Muta-Converter-{version}-Setup.exe'
        return {'tag_name': f'v{version}', 'draft': False, 'prerelease': False,
                'body': '### Fixed\n- An example.', 'assets': [{'name': filename,
                'browser_download_url': f'{WEB_URL}/releases/download/v{version}/{filename}',
                'size': len(payload), 'digest': 'sha256:' + hashlib.sha256(payload).hexdigest()}]}

    def test_semantic_comparison_and_stable_releases(self):
        self.assertIsNotNone(parse_release(self.release_data('0.10.0'), '0.9.0'))
        self.assertIsNone(parse_release(self.release_data('0.2.0'), '0.2.0'))
        self.assertIsNone(parse_release(self.release_data('0.1.0'), '0.2.0'))
        data = self.release_data()
        data['prerelease'] = True
        self.assertIsNone(parse_release(data, '0.1.0'))

    def test_reject_foreign_url_or_missing_hash(self):
        data = self.release_data()
        data['assets'][0]['browser_download_url'] = 'https://example.com/setup.exe'
        with self.assertRaises(ConversionError):
            parse_release(data, '0.1.0')
        data = self.release_data()
        data['assets'][0]['digest'] = None
        with self.assertRaises(ConversionError):
            parse_release(data, '0.1.0')

    def test_verified_download_does_not_execute(self):
        payload = b'installer test bytes'
        release = parse_release(self.release_data(payload=payload), '0.1.0')
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, \
                patch.dict(os.environ, {'MUTA_CONFIG_DIR': folder}), \
                patch('muta.updates.urlopen', return_value=io.BytesIO(payload)), \
                patch('muta.updates.os.startfile', create=True) as launch:
            path = download_installer(release)
            self.assertEqual(path.read_bytes(), payload)
            launch.assert_not_called()

    def test_corrupt_download_removed_and_not_executed(self):
        release = parse_release(self.release_data(), '0.1.0')
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, \
                patch.dict(os.environ, {'MUTA_CONFIG_DIR': folder}), \
                patch('muta.updates.urlopen', return_value=io.BytesIO(b'corrupt')), \
                patch('muta.updates.os.startfile', create=True) as launch:
            with self.assertRaises(ConversionError):
                download_installer(release)
            self.assertEqual(list((Path(folder) / 'updates').iterdir()), [])
            launch.assert_not_called()

    def test_changed_installer_rejected_before_launch(self):
        release = parse_release(self.release_data(), '0.1.0')
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, \
                patch('muta.updates.sys.platform', 'win32'), \
                patch('muta.updates.os.startfile', create=True) as launch:
            path = Path(folder) / 'setup.exe'
            path.write_bytes(b'modified')
            with self.assertRaises(ConversionError):
                launch_installer(path, release)
            launch.assert_not_called()

    def test_verified_installer_uses_normal_uac_prompt(self):
        payload = b'installer test bytes'
        release = parse_release(self.release_data(payload=payload), '0.1.0')
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as folder, \
                patch('muta.updates.sys.platform', 'win32'), \
                patch('muta.updates.os.startfile', create=True) as launch:
            path = Path(folder) / 'setup.exe'
            path.write_bytes(payload)
            launch_installer(path, release)
            launch.assert_called_once_with(str(path), 'runas')
