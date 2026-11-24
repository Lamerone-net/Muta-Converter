from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from PIL import Image

from muta.catalog import family_for
from muta.engines import ConversionError, find_engine
from muta.service import Options, convert, targets_for


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.source = self.root / 'foto con spazi.png'
        Image.new('RGBA', (40, 20), (255, 0, 0, 0)).save(self.source)

    def tearDown(self):
        self.folder.cleanup()

    def test_webp_to_jpg_alpha_and_original(self):
        source = self.root / 'foto.webp'
        Image.new('RGBA', (32, 16), (0, 0, 0, 0)).save(source)
        original = source.read_bytes()
        output = convert(source, 'JPEG')
        with Image.open(output) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(source.read_bytes(), original)

    def test_concurrent_outputs_never_overwrite(self):
        existing = self.source.with_suffix('.jpg')
        existing.write_bytes(b'keep me')
        with ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda _: convert(self.source, 'jpg'), range(4)))
        self.assertEqual(len(set(outputs)), 4)
        self.assertEqual(existing.read_bytes(), b'keep me')
        self.assertTrue(all(path.stat().st_size > 0 for path in outputs))

    def test_transform_options_and_filename(self):
        output = convert(self.source, 'jpg', options=Options(scale=50, rotation=90,
                         background='#000000', name_template='{name}-small-{format}'))
        self.assertEqual(output.name, 'foto con spazi-small-jpg.jpg')
        with Image.open(output) as image:
            self.assertEqual(image.size, (10, 20))
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))

    def test_corrupt_file_does_not_publish(self):
        source = self.root / 'corrupt.webp'
        source.write_text('not an image')
        with self.assertRaises(ConversionError):
            convert(source, 'jpg')
        self.assertFalse(source.with_suffix('.jpg').exists())
        self.assertFalse(list(self.root.glob('.muta-*')))

    def test_animation_requires_explicit_loss(self):
        source = self.root / 'animation.gif'
        Image.new('RGB', (16, 16), 'red').save(source, save_all=True,
            append_images=[Image.new('RGB', (16, 16), 'blue')], duration=100, loop=0)
        with self.assertRaisesRegex(ConversionError, 'fotogrammi'):
            convert(source, 'png')
        self.assertTrue(convert(source, 'png', options=Options(first_frame=True)).is_file())

    def test_reject_invalid_and_same_formats(self):
        for target in ('png', '../../jpg', 'ppt'):
            with self.assertRaises(ConversionError):
                convert(self.source, target)
        self.assertEqual(targets_for(Path('unknown.zzz')), [])

    def test_reject_unsafe_template_and_options(self):
        for options in (Options(name_template='../{name}'), Options(name_template='CON'),
                        Options(scale=0), Options(quality=101), Options(rotation=42)):
            with self.assertRaises(ConversionError):
                convert(self.source, 'jpg', options=options)

    def test_iwork_routing(self):
        for extension, name, output in [('pages', 'document', 'doc'), ('numbers', 'spreadsheet', 'xls'), ('key', 'presentation', 'ppt')]:
            self.assertEqual(family_for(extension).name, name)
            self.assertIn(output, targets_for(Path('test.' + extension), available_only=False))
        self.assertNotIn('ppt', targets_for(Path('test.pages'), available_only=False))

    def test_missing_office_engine_has_actionable_error(self):
        source = self.root / 'test.pages'
        source.write_bytes(b'placeholder')
        with patch('muta.service.find_engine', return_value=None):
            with self.assertRaisesRegex(ConversionError, 'libreoffice'):
                convert(source, 'doc')

    @unittest.skipUnless(find_engine('ffmpeg'), 'FFmpeg non installato')
    def test_real_audio_roundtrip(self):
        source = self.root / 'audio.wav'
        with wave.open(str(source), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(struct.pack('<h', 1000) * 16000)
        mp3 = convert(source, 'mp3')
        restored = convert(mp3, 'wav')
        self.assertNotEqual(restored, source)
        with wave.open(str(restored)) as stream:
            self.assertGreater(stream.getnframes(), 0)


if __name__ == '__main__':
    unittest.main()
