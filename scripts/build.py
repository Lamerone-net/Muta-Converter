"""Build the app and, when available, the Windows graphical installer."""
import argparse
import os
from pathlib import Path
import shutil
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installer', action='store_true', help='Richiede Inno Setup su Windows')
    parser.add_argument('--iscc', type=Path, help='Percorso del compilatore Inno Setup')
    args = parser.parse_args()
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', str(ROOT / 'Muta.spec')], cwd=ROOT, check=True)
    if args.installer:
        if sys.platform != 'win32':
            parser.error('L’installer Inno Setup si costruisce su Windows.')
        compiler = str(args.iscc) if args.iscc else shutil.which('ISCC')
        if not compiler:
            for base in (os.environ.get('ProgramFiles(x86)', ''), os.environ.get('ProgramFiles', ''),
                         str(ROOT / 'build/tools')):
                candidate = Path(base) / 'Inno Setup 6/ISCC.exe'
                if candidate.is_file():
                    compiler = str(candidate)
                    break
        if not compiler:
            parser.error('App creata in dist/Muta. Installa Inno Setup 6 o passa --iscc per generare il setup.')
        version = re.search(r'__version__ = "([^"]+)"', (ROOT / 'src/muta/__init__.py').read_text()).group(1)
        subprocess.run([compiler, f'/DAppVersion={version}', str(ROOT / 'installer/windows.iss')], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
