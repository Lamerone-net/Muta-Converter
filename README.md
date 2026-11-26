# Muta

Muta is a cross-platform file converter by WoollySheep, built in Python for converting files directly from the right-click menu. It supports images, documents, audio, video and Apple iWork files, with a graphical installer, a system tray icon and customizable conversion presets.

Early working version: **0.1.8**. Windows is the first integration target. The conversion core and Qt interface also run on macOS and Linux; their native file-manager integrations are not implemented yet.

## Application

- Graphical Windows installer, defaulting to `C:\Programs\Muta` with administrator rights and an editable destination.
- Tray menu: **Preferences**, **About**, separator, **Quit**.
- English, French, German, Spanish and Italian. The installer language also sets the app and context-menu language.
- Preferences tabs: **Conversion Presets**, **Application**, **Updates**, **About**.
- Create, duplicate, reorder, enable and remove presets. Choose input extensions and output format.
- Preset labels use `MKV - Matroska`, `PPT - PowerPoint`, etc.; legacy generated labels migrate automatically.
- Image quality, scale, rotation, transparency background and explicit first-frame extraction.
- Video CRF, H.264 encoding speed, scale, rotation, audio inclusion and AAC/Opus bitrate.
- PDF image quality/compression, CSV separator, output directory, filename template and external-engine timeout.
- Windows right-click menu with applicable presets. Windows 11 exposes this in **Show more options**.
- **Not mutable** for extensions without any currently available preset. This is a normal text entry; clicking it explains the unavailable conversion. Italic text is not implemented in the static Windows menu.
- Batch conversion from **Preferences → Converti file…** or the CLI. Direct Explorer commands are limited to one selected file.
- Processing stays local. Originals are preserved; collisions receive numbered filenames.

The Windows menu is a snapshot of available engines and enabled presets. Saving preferences updates an installed menu. After installing/removing an external engine, use **Application → Installa / aggiorna menu**. Availability is determined by extension and installed engines, not by inspecting file contents; corrupt, encrypted or incompatible files can still fail.

## Formats and engines

| Family | Example inputs | Outputs | Engine |
| --- | --- | --- | --- |
| Images | JPEG, PNG, WebP, AVIF, GIF, TIFF, BMP, ICO, PSD, DDS, TGA, HEIC/HEIF, SVG | JPG, PNG, WebP, AVIF, GIF, BMP, TIFF, ICO, PDF, SVG | Pillow, resvg, VTracer; optional pillow-heif |
| Documents | DOC, DOCX, ODT, RTF, TXT, **Pages** | DOC, DOCX, ODT, RTF, TXT, PDF, EPUB | LibreOffice |
| Spreadsheets | XLS, XLSX, XLSM, XLSB, ODS, CSV, TSV, **Numbers** | XLS, XLSX, ODS, CSV, PDF | LibreOffice |
| Presentations | PPT, PPTX, PPS, PPSX, ODP, **Keynote** | PPT, PPTX, ODP, PDF | LibreOffice |
| Audio | MP3, WAV, FLAC, AAC, M4A, OGG, Opus, AIFF, WMA | MP3, WAV, FLAC, M4A, OGG, Opus, AIFF | FFmpeg |
| Video | MP4, MKV, MOV, AVI, WebM, MPEG, WMV, FLV, TS, MTS | MP4, MKV, MOV, WebM; audio extraction | FFmpeg |
| Archives | ZIP, 7Z, TAR, TGZ, GZ, TBZ2, BZ2, TXZ, XZ, ARJ, RAR, CAB, LZH | ZIP, 7Z, TAR, TGZ, TBZ2, TXZ | 7-Zip |

The complete catalogue is in `src/muta/catalog.py`. A listed extension is a supported routing option, not a guarantee that every variant or codec is readable.

**SVG conversion dialog:** Starting an SVG-to-bitmap conversion from Explorer or Preferences opens a dialog for that file. Set final width and height in pixels, lock/unlock the aspect ratio, and choose print resolution in DPI. Changes affect only that conversion. DPI controls physical print size without changing pixel count; it is stored in PNG, JPG, TIFF, BMP and PDF. Other output formats show DPI as unavailable; ICO keeps its 256 × 256 canvas. Cancelling stops the batch before any conversion starts. The CLI stays non-interactive: `muta convert --to png --width 1200 --dpi 300 logo.svg` (height is inferred if omitted).

**SVG:** SVG inputs are rasterized with bundled resvg, including nested SVG viewports; PDF output also contains a raster image. Dimensions come from the SVG size/viewBox and the preset scale. Transparent PNG/WebP output, rotation and opaque background settings are supported. SVG support is not identical to a browser; complex filters, text layout and browser-specific features may differ. Fonts must be installed. External images, scripts and HTML content are rejected; raster images must be embedded. Animated SVG requires explicit first-frame export. Input is limited to 32 MiB and rendering to 40 million pixels / 16,384 pixels per side.

Raster images can be traced to **SVG - Scalable Vector Graphics**, using real vector paths rather than an embedded bitmap. Choose color detail (1–8), speckle removal (0–16 pixels), or black and white in Preferences. Tracing is approximate, especially for photos; higher detail increases complexity. Fully transparent pixels remain transparent; partial transparency is blended against the preset background. Tracing is limited to 4 million pixels after scaling. Both operations honor the timeout. Older full-input image presets gain SVG support; customized input filters remain unchanged.

**Archives:** conversion extracts files into temporary storage and repacks them. TAR compression layers are unwrapped for TGZ/TBZ2/TXZ input. ARJ and RAR are input-only. Encrypted archives, symbolic/hard links, special files, duplicate paths and unsafe member paths are rejected. Default extraction limits are 2 GiB and 100,000 entries, configurable per preset. Limits are checked against the member listing before extraction and actual files afterward. File contents and relative paths are retained; permissions and archive-specific metadata can change. Available source formats depend on the installed 7-Zip build. Use a current engine version.

**Apple iWork:** Pages maps to documents, Numbers to spreadsheets, and Keynote to presentations. Import support depends on the file generation and LibreOffice's filters; notably some Keynote versions are unsupported. Exporting back to `.pages`, `.numbers` or `.key` is not supported. macOS package directories, password-protected files and perfect layout preservation are not supported by this initial implementation. Native Apple-app export on macOS is a future adapter.

**Preservation limits:** images are exported without metadata. Animated/multipage images are rejected unless the user explicitly selects first-frame extraction, which discards the remaining frames/pages. PDF is an output format, not an input. CSV retains one sheet and loses formulas/formatting. Video conversions keep the first video stream and optionally the first audio stream, dropping subtitles and extra tracks. MP3 uses VBR quality 2 and OGG quality 5; WAV/AIFF use 16-bit PCM. FFmpeg encoders must exist in the installed build. Same-format transformations are not offered yet.

## Repository layout

```text
Muta/
├── src/muta/                Python application
├── tests/                   Conversion, settings and GUI tests
├── scripts/                 Build entry points and UI preview
├── installer/windows.iss    Graphical Windows setup
├── assets/branding/         Original logo and editable Fireworks source
├── docs/references/         Original right-click and preferences references
├── .github/workflows/       Windows, macOS and Linux builds
├── build/                   Temporary build tools, previews, intermediates (ignored)
├── dist/                    App bundles and installers (ignored)
├── .venv/                   Local Python environment (ignored)
├── Muta.spec                PyInstaller configuration
└── pyproject.toml           Python package and dependencies
```

The supplied images are visual references and branding assets, not application instructions.

## Development

Python 3.11 or later is required. On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[build,heif]"
.\.venv\Scripts\python.exe -m muta --preferences
```

On macOS/Linux, use `.venv/bin/python` instead. Install FFmpeg, LibreOffice and 7-Zip separately to enable their formats. They are not bundled in the application installer. Their executable paths can be configured in Preferences, or with `MUTA_FFMPEG`, `MUTA_LIBREOFFICE` and `MUTA_7ZIP`. A saved preference takes precedence over the environment variable.

```powershell
# Start directly in the tray
.\.venv\Scripts\python.exe -m muta --tray

# Check engines and available targets
.\.venv\Scripts\python.exe -m muta doctor
.\.venv\Scripts\python.exe -m muta formats "C:\Images\photo.webp"

# Convert one or more files (leave originals untouched)
.\.venv\Scripts\python.exe -m muta convert --to jpg -- "C:\Images\photo.webp"
.\.venv\Scripts\python.exe -m muta convert --preset document_doc -- "C:\Docs\document.pages"
.\.venv\Scripts\python.exe -m muta convert --to odt -- "C:\Docs\document.docx"
.\.venv\Scripts\python.exe -m muta convert --to zip -- "C:\Archives\backup.tgz"

# GUI progress, also used by Explorer
.\.venv\Scripts\python.exe -m muta convert --to jpg --notify -- "C:\Images\photo.webp"

# Install/remove only Muta's current-user menu entries
.\.venv\Scripts\python.exe -m muta shell install
.\.venv\Scripts\python.exe -m muta shell remove
```

Use the packaged `muta-cli.exe` for terminal commands; `Muta.exe` is the windowless GUI executable. Each conversion is run in a temporary directory and published only after the engine succeeds. Publication reserves a unique output name exclusively, preventing simultaneous conversions from overwriting each other. An external process reading the output during the final copy may observe a partially written file; a machine/process crash during publication can leave a partial file. Failed conversions handled by Muta clean up their outputs.

Preferences are stored in `%APPDATA%\MutaConverter\settings.json` on Windows, `~/Library/Application Support/MutaConverter` on macOS and `$XDG_CONFIG_HOME/muta-converter` (normally `~/.config/muta-converter`) on Linux. These internal paths retain their original names so upgrades keep existing settings. `MUTA_CONFIG_DIR` overrides this for development. Only one tray instance per configuration is allowed. Closing Preferences keeps the tray running when a tray is available. Without a tray, Preferences remains the application's main window.

## Build

```powershell
# Build dist/Muta/Muta.exe and dist/Muta/muta-cli.exe
.\.venv\Scripts\python.exe scripts/build.py

# Build the graphical setup too (requires Inno Setup 6)
.\.venv\Scripts\python.exe scripts/build.py --installer

# Or use an explicit Inno Setup compiler path
.\.venv\Scripts\python.exe scripts/build.py --installer --iscc "C:\Tools\Inno Setup 6\ISCC.exe"
```

The Windows installer is written to `dist/installer/Muta-<version>-Setup.exe`. Its default destination is `<system drive>\Programs\Muta` (normally `C:\Programs\Muta`), not AppData. The destination page remains visible, and installation requires administrator privileges. This is an x64 build, so it does not use a `(x86)` folder. It always installs or refreshes the context menu for the current user. This is a required feature, with no installer checkbox or removal button in Preferences. Startup at login and the desktop shortcut remain optional. It then starts the tray app as the original user. Uninstall removes Muta's menu and startup entry for the uninstalling account while retaining user preferences and converted files. This initial installer is unsigned.

Build on each target operating system: PyInstaller does not cross-compile Windows, macOS and Linux apps from a single host. The GitHub Actions workflow prepares native builds. The macOS output includes an `.app`, while Linux produces an application folder. macOS notarization, Linux desktop packages and native Finder/file-manager menus remain future work. Windows packaging currently targets x64.

## Versions and GitHub Releases

`src/muta/__init__.py` is the single source of the application version. Python packaging, About, the Windows installer and macOS bundle all use it. `CHANGELOG.md` records changes in English using Semantic Versioning (`MAJOR.MINOR.PATCH`).

For each new release:

1. Add human-readable changes under `[Unreleased]` in `CHANGELOG.md`.
2. Run `python scripts/release.py 0.2.0` (choose the appropriate next version). This updates the version and moves pending changes into a dated section.
3. Review and test, then commit the release changes.
4. Create the matching tag with `git tag v0.2.0` and push the branch and tag to GitHub.

Pushing a version tag runs `.github/workflows/release.yml`: check version/tag/changelog consistency, test and build all three platforms, then publish a GitHub Release with the matching changelog section and versioned archives/Windows installer. Publication only happens if every platform build succeeds. Existing tags can be retried using the workflow's manual `tag` input. The initial release uses `v0.1.0` and its existing changelog entry; no version bump is needed for it.

Main-branch pushes and pull requests run build/tests without publishing. Build artefacts are ignored by Git; releases hold downloadable binaries.

The official product name is **Muta**. The repository URL remains `Lamerone-net/Muta-Converter` for update compatibility. Release downloads use `Muta-<version>-…`; an identical `Muta-Converter-<version>-Setup.exe` alias lets versions up to 0.1.3 discover new installers. Windows upgrades preserve the installation directory and installer identity; fresh installations default to `C:\Programs\Muta`.

## User-controlled updates

**Preferences → Updates → Controlla aggiornamenti** queries the public GitHub Releases API for the latest stable version. Startup checks are optional and disabled by default. A newer version displays its changelog and asks permission to download. On Windows the installer must be an official repository release asset with a valid GitHub-provided SHA-256 digest and expected size. The download is checked before being retained, and checked again immediately before execution.

After download, a second confirmation asks whether to close Muta and launch the interactive installer. Declining either prompt does not install anything. Muta never silently installs an update. On macOS/Linux, confirmation opens the official release page for manual installation. Downloads are cached in the user configuration's `updates/` directory. A network error or missing checksum leaves the current application unchanged.

SHA-256 verification detects corruption or a file changed after download; it is not publisher code signing. The initial installer remains unsigned. Update metadata and downloads come only from GitHub; conversion files are never uploaded.

## Language

The installer offers English, French, German, Spanish and Italian. It saves the selected language before registering the Explorer menu and launching the tray app. English installs display `Muta · Convert to`; changing the installation language also refreshes existing Muta menu entries.

Change language later in **Preferences → Application → Language**, then save. The installed context menu changes immediately; restart Muta to apply the new language to the open interface and tray. Custom preset names are preserved. Update installers receive the selected language automatically. Existing settings without a language keep Italian until changed in Preferences or by the new installer.

Translation catalogues live in `src/muta/locales/`. Qt button/dialog translations are bundled. Technical format and codec names, external-tool output and release notes supplied by GitHub remain in their original language. For development, `muta configure --language en` persists the language; `scripts/preview_ui.py --all` renders all five interfaces.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/preview_ui.py
```

Tests exercise actual image conversion, concurrency/collisions, corrupt inputs, explicit animation flattening, iWork routing, settings persistence, unavailable-engine handling, menu generation, Qt preset editing and release preparation. An actual audio roundtrip runs when FFmpeg is available; archive roundtrips and malicious-path rejection run with 7-Zip. LibreOffice/iWork fidelity, Explorer rendering, tray interactions and installation/uninstallation require native integration checks; unit tests do not establish those results.

## Technical references

- [Pillow image formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- [LibreOffice conversion filters](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html)
- [Apple iWork export families](https://support.apple.com/en-gb/105050)
- [FFmpeg command-line documentation](https://ffmpeg.org/ffmpeg.html)
- [7-Zip supported formats](https://www.7-zip.org/)
- [Qt system tray API](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html)
- [Windows context-menu conditions](https://devblogs.microsoft.com/oldnewthing/20130207-00/?p=5323)
- [Modern Windows Explorer integration](https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/integrate-packaged-app-with-file-explorer)
- [PyInstaller platform requirements](https://pyinstaller.org/en/stable/requirements.html)
- [Inno Setup documentation](https://jrsoftware.org/inno-setup/documentation/)

## Updating on Windows

Install a newer setup over the existing installation; normally no uninstall, sign-out or reboot is needed. Finish conversions, choose **Quit** from the Muta tray menu, run the new installer and start Muta again. Verify the version in **About**. Installation refreshes an existing context menu and migrates preferences. If needed, use **Preferences → Application → Install / update menu**. A fresh installation defaults to `C:\Programs\Muta`; upgrades can retain the older `Muta Converter` folder name. The folder name does not indicate the version. GitHub releases and local `dist` builds are separate files; always check the version in the setup filename.
