"""Create versioned, executable-preserving release archives."""
from pathlib import Path
import platform
import shutil
import sys
from release import current_version

root = Path(__file__).resolve().parents[1]
output = root / 'build/release'
output.mkdir(parents=True, exist_ok=True)
version = current_version()
system = {'win32': 'Windows', 'darwin': 'macOS'}.get(sys.platform, 'Linux')
base = output / f'Muta-{version}-{system}-{platform.machine()}'
if sys.platform == 'win32':
    shutil.make_archive(str(base), 'zip', root / 'dist', 'Muta')
    installer = root / f'dist/installer/Muta-{version}-Setup.exe'
    if installer.is_file():
        shutil.copy2(installer, output / installer.name)
        # Versions <= 0.1.3 discover updates by this exact legacy filename.
        shutil.copy2(installer, output / f'Muta-Converter-{version}-Setup.exe')
else:
    folder = 'Muta.app' if sys.platform == 'darwin' else 'Muta'
    shutil.make_archive(str(base), 'gztar', root / 'dist', folder)
print(output)
