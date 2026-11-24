# Third-party components

Muta uses Python, Pillow, Qt for Python (PySide6-Essentials and Shiboken6), and optionally pillow-heif. The packaged application includes their available distribution metadata and license files under `_internal`.

- Python: https://docs.python.org/3/license.html
- Pillow: https://github.com/python-pillow/Pillow/blob/main/LICENSE
- Qt for Python: https://doc.qt.io/qtforpython-6/licenses.html
- pillow-heif / libheif: https://github.com/bigcat88/pillow_heif
- PyInstaller bootloader: https://pyinstaller.org/en/stable/license.html

FFmpeg, LibreOffice and 7-Zip are detected from the user's machine; their binaries are not redistributed in the initial installer.

Inno Setup is a build-time tool and is not bundled in the application directory. Its setup/uninstall runtime is part of the generated Windows installer.
