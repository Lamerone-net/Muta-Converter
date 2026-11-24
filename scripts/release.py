"""Prepare a release from the Unreleased changelog section; never commits or pushes."""
import argparse
from datetime import datetime
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def current_version(root=ROOT):
    return re.search(r'__version__ = "([^"]+)"', (root / 'src/muta/__init__.py').read_text()).group(1)


def notes(version, root=ROOT):
    text = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(r'^## \[' + re.escape(version) + r'\][^\n]*\n(.*?)(?=^## \[|\Z)', text, re.M | re.S)
    if not match or not match.group(1).strip():
        raise ValueError(f'No changelog entry for {version}')
    return match.group(1).strip() + '\n'


def prepare(version, root=ROOT):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Use a stable semantic version: MAJOR.MINOR.PATCH')
    old = current_version(root)
    if tuple(map(int, version.split('.'))) <= tuple(map(int, old.split('.'))):
        raise ValueError(f'Version must be newer than {old}')
    path = root / 'CHANGELOG.md'
    changelog = path.read_text(encoding='utf-8')
    match = re.search(r'^## \[Unreleased\]\s*\n(.*?)(?=^## \[|\Z)', changelog, re.M | re.S)
    if not match or not match.group(1).strip():
        raise ValueError('Add changes to the Unreleased section before releasing')
    date = datetime.now().astimezone().date().isoformat()
    heading = f'## [Unreleased]\n\n## [{version}] - {date}\n\n'
    updated = changelog[:match.start()] + heading + match.group(1).strip() + '\n\n' + changelog[match.end():]
    module = root / 'src/muta/__init__.py'
    source = module.read_text(encoding='utf-8').replace(f'__version__ = "{old}"', f'__version__ = "{version}"')
    path.write_text(updated, encoding='utf-8')
    module.write_text(source, encoding='utf-8')
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?')
    parser.add_argument('--notes', action='store_true')
    parser.add_argument('--check-tag', help='Check version, tag and changelog match')
    args = parser.parse_args()
    try:
        version = current_version()
        if args.check_tag:
            if args.check_tag != f'v{version}':
                raise ValueError(f'Tag {args.check_tag} differs from app version v{version}')
            notes(version)
            print(version)
        elif args.notes:
            print(notes(args.version or version), end='')
        elif args.version:
            print(f'Prepared {prepare(args.version)}. Review the diff, commit, tag and push to release.')
        else:
            print(version)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
