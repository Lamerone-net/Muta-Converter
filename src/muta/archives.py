"""7-Zip archive conversion with isolated extraction and checked member paths."""

from .i18n import tr
from pathlib import Path, PurePosixPath
import re
import tempfile

from .engines import ConversionError, run_process


def check_members(listing: str, options) -> None:
    entries = []
    current = {}
    for line in listing.splitlines() + ['']:
        if not line.strip():
            if 'Path' in current:
                entries.append(current)
            current = {}
        elif ' = ' in line:
            key, value = line.split(' = ', 1)
            current[key] = value
    if len(entries) > options.archive_max_files:
        raise ConversionError(tr('L’archivio supera il limite di elementi configurato.'))
    total = 0
    seen = set()
    for entry in entries:
        name = entry['Path'].replace('\\', '/')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or ':' in name or '\x00' in name:
            raise ConversionError(tr('Percorso non sicuro nell’archivio: {0}', name))
        if any(part.rstrip(' .') != part for part in path.parts):
            raise ConversionError(tr('Percorso ambiguo nell’archivio: {0}', name))
        if any(part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
               *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]} for part in path.parts):
            raise ConversionError(tr('Nome riservato nell’archivio: {0}', name))
        if name in ('.', './'):
            continue
        key = str(path).casefold()
        if key in seen:
            raise ConversionError(tr('Percorsi duplicati nell’archivio: {0}', name))
        seen.add(key)
        attributes = entry.get('Attributes', '') + ' ' + entry.get('Mode', '')
        if (entry.get('Symbolic Link') or entry.get('Hard Link') or entry.get('Alternate Stream') == '+'
                or re.search(r'(^|\s)[lcbps][rwxstST-]{9}', attributes)):
            raise ConversionError(tr('Archivi con collegamenti, flussi alternativi o file speciali non supportati.'))
        if entry.get('Encrypted') == '+':
            raise ConversionError(tr('Gli archivi protetti da password non sono ancora supportati.'))
        try:
            size = int(entry.get('Size', '0') or '0')
        except ValueError as exc:
            raise ConversionError(tr('Dimensione di un elemento non determinabile.')) from exc
        if size < 0:
            raise ConversionError(tr('Dimensione non valida nell’archivio.'))
        total += size
    if total > options.archive_limit_mb * 1024 * 1024:
        raise ConversionError(tr('L’archivio supera il limite di dimensione estratta configurato.'))


def extract(source, directory, executable, options):
    listing = run_process([executable, 'l', '-slt', '-ba', '-sccUTF-8', '-pMUTA-NO-PASSWORD',
                           '--', str(source)], options.timeout)
    check_members(listing, options)
    directory.mkdir()
    run_process([executable, 'x', '-y', '-bd', '-sccUTF-8', '-pMUTA-NO-PASSWORD',
                 f'-o{directory}', '--', str(source)], options.timeout)
    total = 0
    count = 0
    for path in directory.rglob('*'):
        count += 1
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ConversionError(tr('Collegamento inatteso nell’archivio estratto.'))
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ConversionError(tr('Percorso estratto esterno alla cartella temporanea.'))
        if path.is_file():
            total += path.stat().st_size
        elif not path.is_dir():
            raise ConversionError(tr('File speciale non supportato.'))
    if total > options.archive_limit_mb * 1024 * 1024 or count > options.archive_max_files:
        raise ConversionError(tr('L’archivio estratto supera i limiti configurati.'))


def convert_archive(source, destination, target, executable, options):
    with tempfile.TemporaryDirectory(prefix='archive-', dir=destination.parent) as folder:
        root = Path(folder)
        contents = root / 'contents'
        extract(source, contents, executable, options)
        # TGZ/TBZ2/TXZ are compressed TAR streams: unwrap both layers.
        if source.suffix.lower() in {'.tgz', '.gz', '.tbz', '.tbz2', '.bz2', '.txz', '.xz'}:
            children = list(contents.iterdir())
            if len(children) == 1 and children[0].suffix.lower() == '.tar':
                unpacked = root / 'unpacked'
                extract(children[0], unpacked, executable, options)
                contents = unpacked
        compression = {'tgz': 'gzip', 'tbz2': 'bzip2', 'txz': 'xz'}.get(target)
        if compression:
            tar = root / 'payload.tar'
            run_process([executable, 'a', '-ttar', '-y', '-bd', str(tar), '.'], options.timeout, cwd=contents)
            # The payload name inside a gzip stream identifies it as a tar on the return trip.
            run_process([executable, 'a', f'-t{compression}', f'-mx={options.archive_level}',
                         '-y', '-bd', str(destination), str(tar)], options.timeout)
        else:
            args = [executable, 'a', f'-t{target}', '-y', '-bd']
            if target != 'tar':
                args += [f'-mx={options.archive_level}']
            run_process([*args, str(destination), '.'], options.timeout, cwd=contents)
