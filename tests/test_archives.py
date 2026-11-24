from pathlib import Path
import tempfile
import unittest
import zipfile

from muta.archives import check_members
from muta.engines import ConversionError, find_engine
from muta.service import Options, convert


class ArchiveValidationTests(unittest.TestCase):
    def test_unsafe_members_rejected(self):
        for name in ('../escape.txt', '/absolute', 'C:\\escape.txt', 'folder/../../escape', 'NUL.txt'):
            with self.assertRaises(ConversionError):
                check_members(f'Path = {name}\nSize = 2\n', Options())
        for extra in ('Symbolic Link = /etc/passwd', 'Hard Link = target', 'Encrypted = +'):
            with self.assertRaises(ConversionError):
                check_members(f'Path = link\nSize = 2\n{extra}\n', Options())

    def test_declared_limits_and_duplicate_paths(self):
        with self.assertRaises(ConversionError):
            check_members('Path = large\nSize = 2097152\n', Options(archive_limit_mb=1))
        with self.assertRaises(ConversionError):
            check_members('Path = FILE\nSize = 1\n\nPath = file\nSize = 1\n', Options())


@unittest.skipUnless(find_engine('sevenzip'), '7-Zip non installato')
class ArchiveConversionTests(unittest.TestCase):
    def test_real_roundtrips_preserve_paths_and_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'original.zip'
            payloads = {'nested/test.txt': b'hello world', 'data.bin': bytes(range(256)), '.hidden': b'kept'}
            with zipfile.ZipFile(source, 'w') as archive:
                for name, payload in payloads.items():
                    archive.writestr(name, payload)
            original = source.read_bytes()
            for target in ('7z', 'tar', 'tgz', 'tbz2', 'txz'):
                with self.subTest(target=target):
                    packed = convert(source, target)
                    restored = convert(packed, 'zip')
                    with zipfile.ZipFile(restored) as archive:
                        actual = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
                    self.assertEqual(actual, payloads)
            self.assertEqual(source.read_bytes(), original)

    def test_traversal_archive_not_extracted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bad.zip'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('../escaped.txt', 'do not extract')
            with self.assertRaises(ConversionError):
                convert(source, '7z')
            self.assertFalse((root / 'escaped.txt').exists())
            self.assertFalse(source.with_suffix('.7z').exists())
