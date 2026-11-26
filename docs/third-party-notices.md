# Third-party components

Muta uses Python, Pillow, Qt for Python (PySide6-Essentials and Shiboken6), and optionally pillow-heif. The packaged application includes their available distribution metadata and license files under `_internal`.

- Python: https://docs.python.org/3/license.html
- Pillow: https://github.com/python-pillow/Pillow/blob/main/LICENSE
- Qt for Python: https://doc.qt.io/qtforpython-6/licenses.html
- pillow-heif / libheif: https://github.com/bigcat88/pillow_heif
- PyInstaller bootloader: https://pyinstaller.org/en/stable/license.html
- defusedxml (SVG XML parsing): https://github.com/tiran/defusedxml/blob/main/LICENSE
- VTracer (SVG vector tracing, MIT): https://github.com/visioncortex/vtracer

SVG dimensions are inspected with Qt SVG; raster rendering uses resvg via resvg_py, including support for nested SVG viewports. VTracer, defusedxml and resvg_py are bundled with their distribution metadata and license files.

- resvg_py / resvg: https://github.com/baseplate-admin/resvg-py and https://github.com/linebender/resvg

FFmpeg, LibreOffice and 7-Zip are detected from the user's machine; their binaries are not redistributed in the initial installer.

Inno Setup is a build-time tool and is not bundled in the application directory. Its setup/uninstall runtime is part of the generated Windows installer.
