"""Opt-in release checks and verified downloads. Installation is a separate action."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .engines import ConversionError
from .settings import config_dir

REPOSITORY = 'Lamerone-net/Muta-Converter'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
WEB_URL = f'https://github.com/{REPOSITORY}'
MAX_INSTALLER_SIZE = 1024 * 1024 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    page_url: str
    installer_url: str | None
    sha256: str | None
    size: int = 0


def version_tuple(version):
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ConversionError('Versione della release non valida.')
    return tuple(map(int, version.split('.')))


def parse_release(data, current_version) -> Release | None:
    if data.get('draft') or data.get('prerelease'):
        return None
    tag = data.get('tag_name', '')
    version = tag.removeprefix('v')
    if version_tuple(version) <= version_tuple(current_version):
        return None
    filename = f'Muta-Converter-{version}-Setup.exe'
    expected = f'{WEB_URL}/releases/download/{tag}/{filename}'
    asset = next((asset for asset in data.get('assets', []) if asset.get('name') == filename), None)
    url = digest = None
    size = 0
    if asset:
        if asset.get('browser_download_url') != expected:
            raise ConversionError('Il download non appartiene alla release ufficiale di Muta.')
        checksum = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', checksum):
            raise ConversionError('La release non contiene un checksum SHA-256 verificabile.')
        size = asset.get('size', 0)
        if type(size) is not int or not 0 < size <= MAX_INSTALLER_SIZE:
            raise ConversionError('Dimensione installer non valida.')
        url, digest = expected, checksum.split(':', 1)[1].lower()
    return Release(version, str(data.get('body') or ''), f'{WEB_URL}/releases/tag/{tag}', url, digest, size)


def check_latest(current_version) -> Release | None:
    request = Request(API_URL, headers={'Accept': 'application/vnd.github+json',
        'User-Agent': 'Muta-Converter', 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ConversionError('Risposta aggiornamenti troppo grande.')
        return parse_release(json.loads(payload), current_version)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise ConversionError(f'GitHub non disponibile (HTTP {exc.code}). Riprova più tardi.') from exc
    except (URLError, TimeoutError, OSError, ValueError, TypeError, AttributeError) as exc:
        raise ConversionError(f'Impossibile controllare gli aggiornamenti: {exc}') from exc


def download_installer(release: Release, progress=lambda value: None) -> Path:
    if not release.installer_url or not release.sha256:
        raise ConversionError('Installer Windows non disponibile per questa release.')
    folder = config_dir() / 'updates'
    folder.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='muta-', suffix='.part', dir=folder)
    partial = Path(name)
    digest = hashlib.sha256()
    count = 0
    started = time.monotonic()
    try:
        request = Request(release.installer_url, headers={'User-Agent': 'Muta-Converter'})
        with os.fdopen(handle, 'wb') as output, urlopen(request, timeout=30) as response:
            while chunk := response.read(1024 * 1024):
                if time.monotonic() - started > 600:
                    raise ConversionError('Download interrotto: tempo massimo superato.')
                count += len(chunk)
                if count > release.size or count > MAX_INSTALLER_SIZE:
                    raise ConversionError('Il download supera la dimensione attesa.')
                digest.update(chunk)
                output.write(chunk)
                progress(round(count * 100 / release.size))
        if count != release.size or digest.hexdigest() != release.sha256:
            raise ConversionError('Verifica SHA-256 fallita. Il file non verrà eseguito.')
        destination = folder / f'Muta-Converter-{release.version}-Setup.exe'
        os.replace(partial, destination)
        return destination
    except (OSError, URLError, TimeoutError) as exc:
        raise ConversionError(f'Download non riuscito: {exc}') from exc
    finally:
        partial.unlink(missing_ok=True)


def launch_installer(path: Path, release: Release) -> None:
    if sys.platform != 'win32':
        raise ConversionError('L’installazione automatizzata è disponibile solo su Windows.')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != release.sha256:
        raise ConversionError('Il file è cambiato dopo il download: installazione annullata.')
    # Interactive setup only. The GUI calls this solely after explicit confirmation.
    # ShellExecute's runas verb opens the normal Windows UAC consent prompt.
    os.startfile(str(path), 'runas')
