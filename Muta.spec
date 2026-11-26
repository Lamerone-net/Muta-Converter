# Build on the target OS: Windows, macOS or Linux.
from pathlib import Path
import sys
import re
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

root = Path(SPECPATH)
version = re.search(r'__version__ = "([^"]+)"', (root / 'src/muta/__init__.py').read_text()).group(1)
metadata = []
for package in ('Pillow', 'PySide6-Essentials', 'shiboken6', 'pillow-heif', 'defusedxml', 'vtracer'):
    metadata += copy_metadata(package)
analysis = Analysis(
    [str(root / 'scripts/launcher.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[(str(root / 'assets/branding/logo.png'), 'assets/branding'),
           (str(root / 'assets/branding/icon.ico'), 'assets/branding'),
           (str(root / 'docs/third-party-notices.md'), '.'), *metadata,
           *collect_data_files('muta', includes=['locales/*.json']),
           *collect_data_files('PySide6', includes=[f'**/qtbase_{code}.qm' for code in ('en', 'fr', 'de', 'es', 'it')])],
    hiddenimports=['pillow_heif'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml',
              'PySide6.QtQuick', 'tkinter', 'pytest'],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
gui = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='Muta',
          console=False, debug=False, strip=False, upx=False,
          icon=str(root / 'assets/branding/icon.ico') if sys.platform == 'win32' else None)
cli = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='muta-cli',
          console=True, debug=False, strip=False, upx=False,
          icon=str(root / 'assets/branding/icon.ico') if sys.platform == 'win32' else None)
collection = COLLECT(gui, cli, analysis.binaries, analysis.datas,
                     strip=False, upx=False, name='Muta')
if sys.platform == 'darwin':
    bundle = BUNDLE(collection, name='Muta.app', bundle_identifier='net.lamerone.muta',
                    info_plist={'LSUIElement': True, 'CFBundleShortVersionString': version})
