# Third-party components

Muta uses Python, Pillow, Qt for Python (PySide6-Essentials and Shiboken6), and optionally pillow-heif. The packaged application includes their available distribution metadata and license files under `_internal`.

- Python: https://docs.python.org/3/license.html
- Pillow: https://github.com/python-pillow/Pillow/blob/main/LICENSE
- Qt for Python: https://doc.qt.io/qtforpython-6/licenses.html
- pillow-heif / libheif: https://github.com/bigcat88/pillow_heif
- PyInstaller bootloader: https://pyinstaller.org/en/stable/license.html
- defusedxml (SVG XML parsing): https://github.com/tiran/defusedxml/blob/main/LICENSE
- VTracer (SVG vector tracing, MIT): https://github.com/visioncortex/vtracer

SVG rendering uses the Qt SVG module included with Qt for Python. VTracer and defusedxml are bundled with their distribution metadata and license files.

FFmpeg, LibreOffice and 7-Zip are detected from the user's machine; their binaries are not redistributed in the initial installer.

Inno Setup is a build-time tool and is not bundled in the application directory. Its setup/uninstall runtime is part of the generated Windows installer.
