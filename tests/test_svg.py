from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw

from muta.engines import ConversionError
from muta.integration import menu_entries
from muta.service import Options, convert, targets_for
from muta.settings import Settings, load_settings, save_settings

TEMP_ROOT = Path(__file__).resolve().parents[1] / '.test-output'
TEMP_ROOT.mkdir(exist_ok=True)


class SvgTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=TEMP_ROOT)
        self.root = Path(self.folder.name)
        self.svg = self.root / 'drawing.SVG'
        self.data = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40"><rect width="40" height="40" fill="#ff0000"/></svg>'
        self.svg.write_bytes(self.data)

    def tearDown(self):
        self.folder.cleanup()

    def test_render_transparency_scale_rotation_and_original(self):
        output = convert(self.svg, 'png', options=Options(scale=200, rotation=90))
        with Image.open(output) as image:
            self.assertEqual(image.size, (80, 160))
            self.assertEqual(image.getpixel((40, 40)), (255, 0, 0, 255))
            self.assertEqual(image.getpixel((40, 120))[3], 0)
        self.assertEqual(self.svg.read_bytes(), self.data)

    def test_svg_outputs_and_background(self):
        for target in targets_for(self.svg):
            with self.subTest(target=target):
                output = convert(self.svg, target, options=Options(background='#00ff00'))
                if target == 'pdf':
                    self.assertTrue(output.read_bytes().startswith(b'%PDF'))
                else:
                    with Image.open(output) as image:
                        self.assertGreater(image.width, 0)
                        if target == 'jpg':
                            pixel = image.convert('RGB').getpixel((70, 20))
                            self.assertGreater(pixel[1], 240)
                            self.assertLess(pixel[0], 15)

    def test_requested_output_size_rotation_and_dpi(self):
        options = Options(svg_width=60, svg_height=120, svg_dpi=300, rotation=90)
        for target in ('png', 'jpg', 'tiff', 'bmp'):
            output = convert(self.svg, target, options=options)
            with Image.open(output) as image:
                self.assertEqual(image.size, (60, 120))
                self.assertAlmostEqual(image.info['dpi'][0], 300, delta=0.1)
        output = convert(self.svg, 'png', options=Options(svg_width=160))
        with Image.open(output) as image:
            self.assertEqual(image.size, (160, 80))
        pdf = convert(self.svg, 'pdf', options=Options(svg_width=300, svg_height=150, svg_dpi=300))
        self.assertRegex(pdf.read_bytes(), rb'/MediaBox\s*\[\s*0\s+0\s+72\.0\s+36\.0\s*\]')

    def test_nested_svg_viewports_are_visible_scaled_and_clipped(self):
        # Synthetic reproduction of a QR-export layout; no user artwork is stored.
        self.svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <svg x="10" y="20" width="80" height="60" viewBox="0 0 800 600">
            <rect width="800" height="600" fill="white"/>
            <svg x="200" y="100" width="400" height="400" viewBox="0 0 40 40">
              <rect width="80" height="40" fill="black"/>
            </svg>
          </svg>
        </svg>''')
        output = convert(self.svg, 'png', options=Options(svg_width=200, svg_height=100, svg_dpi=300))
        with Image.open(output) as image:
            self.assertEqual(image.size, (200, 100))
            self.assertEqual(image.getpixel((100, 50)), (0, 0, 0, 255))
            self.assertEqual(image.getpixel((30, 25)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((150, 50)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((5, 5))[3], 0)
            self.assertEqual(image.getpixel((185, 50))[3], 0)
            self.assertAlmostEqual(image.info['dpi'][0], 300, delta=0.1)

    def test_true_vector_paths_from_png_and_jpg(self):
        for suffix in ('png', 'jpg'):
            with self.subTest(suffix=suffix):
                source = self.root / ('blocks.' + suffix)
                raster = Image.new('RGB', (80, 40), 'white')
                ImageDraw.Draw(raster).rectangle((0, 0, 39, 39), fill='red')
                raster.save(source)
                output = convert(source, 'svg', options=Options(scale=50, rotation=90, svg_speckle=0))
                tree = ET.parse(output)
                self.assertEqual((tree.getroot().get('width'), tree.getroot().get('height')), ('20', '40'))
                self.assertTrue(tree.findall('.//{http://www.w3.org/2000/svg}path'))
                self.assertFalse(tree.findall('.//{http://www.w3.org/2000/svg}image'))
                rendered = convert(output, 'png')
                with Image.open(rendered) as image:
                    pixel = image.convert('RGB').getpixel((10, 10))
                    self.assertGreater(pixel[0], 220)
                    self.assertLess(pixel[1], 30)

    def test_vector_transparent_background_and_monochrome(self):
        source = self.root / 'logo.png'
        raster = Image.new('RGBA', (40, 40))
        ImageDraw.Draw(raster).rectangle((10, 10, 30, 30), fill='black')
        raster.save(source)
        for monochrome in (False, True):
            output = convert(source, 'svg', options=Options(svg_speckle=0, svg_monochrome=monochrome))
            rendered = convert(output, 'png')
            with Image.open(rendered) as image:
                self.assertEqual(image.getpixel((0, 0))[3], 0)
                self.assertEqual(image.getpixel((20, 20)), (0, 0, 0, 255))

    def test_invalid_external_and_entity_files_do_not_publish(self):
        contents = [b'not xml', b'<html/>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///private.png"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>',
            b'<!DOCTYPE svg [<!ENTITY test "expanded">]><svg xmlns="http://www.w3.org/2000/svg">&test;</svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg" width="100000" height="100000"/>']
        for data in contents:
            self.svg.write_bytes(data)
            with self.subTest(data=data), self.assertRaises(ConversionError):
                convert(self.svg, 'png')
            self.assertFalse(self.svg.with_suffix('.png').exists())
            self.assertFalse(list(self.root.glob('.muta-*')))

    def test_animation_requires_explicit_static_export(self):
        self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40"><animate attributeName="x" from="0" to="10" dur="2s"/></rect></svg>')
        with self.assertRaises(ConversionError):
            convert(self.svg, 'png')
        self.assertTrue(convert(self.svg, 'png', options=Options(first_frame=True)).is_file())

    def test_trace_limits_and_options(self):
        source = self.root / 'large.png'
        Image.new('RGB', (2100, 2100), 'red').save(source)
        with self.assertRaises(ConversionError):
            convert(source, 'svg')
        self.assertFalse(source.with_suffix('.svg').exists())
        for options in (Options(svg_color_precision=0), Options(svg_speckle=17)):
            with self.assertRaises(ConversionError):
                options.validate()

    def test_upgrade_preserves_choices_and_adds_svg_once(self):
        with patch.dict(os.environ, {'MUTA_CONFIG_DIR': str(self.root)}):
            settings = Settings(language='en')
            settings.presets = [p for p in settings.presets if p.id != 'image_svg']
            for preset in settings.presets:
                preset.inputs = [x for x in preset.inputs if x != 'svg']
            settings.preset('image_jpg').options = replace(Options(), quality=77)
            settings.preset('image_png').inputs = ['webp']
            settings.preset('image_webp').enabled = False
            save_settings(settings)
            path = self.root / 'settings.json'
            data = json.loads(path.read_text())
            data['version'] = 2
            path.write_text(json.dumps(data))
            loaded = load_settings()
            self.assertIn('svg', loaded.preset('image_jpg').inputs)
            self.assertEqual(loaded.preset('image_jpg').options.quality, 77)
            self.assertEqual(loaded.preset('image_png').inputs, ['webp'])
            self.assertFalse(next(p for p in loaded.presets if p.id == 'image_webp').enabled)
            entries = menu_entries(loaded)
            self.assertIn('svg', entries)
            self.assertIn('image_svg', [p[0] for p in entries['png']])
            loaded.presets = [p for p in loaded.presets if p.id != 'image_svg']
            loaded.preset('image_jpg').inputs.remove('svg')
            save_settings(loaded)
            reloaded = load_settings()
            self.assertNotIn('image_svg', [p.id for p in reloaded.presets])
            self.assertNotIn('svg', reloaded.preset('image_jpg').inputs)
