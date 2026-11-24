# Changelog

All notable changes are recorded here. Versions follow Semantic Versioning.

## [Unreleased]

## [0.1.1] - 2026-11-24

### Fixed

- Use the supplied `icon.ico` for Explorer menus, the system tray, application windows, Windows executables and the installer, avoiding distortion of the rectangular logo.

## [0.1.0] - 2026-11-24

### Added

- Python conversion core for images, office documents, spreadsheets, presentations, audio and video.
- Archive conversion through 7-Zip: ZIP, 7Z, TAR, TGZ, TBZ2 and TXZ output; ARJ, RAR and other archives as inputs.
- Configurable archive compression and extraction limits, with rejection of unsafe paths, links and password-protected members.
- Apple iWork import routes: Pages to Word/OpenDocument, Numbers to Excel/OpenDocument, Keynote to PowerPoint/OpenDocument, with LibreOffice compatibility limitations.
- Windows context menu with available conversion presets and a `Not mutable` entry for unavailable extensions.
- System tray with Preferences, About and Quit.
- Editable conversion presets, input formats, quality, resize, rotation, media encoding, PDF and CSV settings.
- Graphical Windows installer with optional startup and context-menu integration.
- Batch conversion, command-line interface, progress and error reporting.
- Original preservation, unique output names, safe concurrent publication and explicit first-frame extraction.
- Windows, macOS and Linux build workflows, versioned GitHub Releases and release notes.
- Opt-in update checks against stable GitHub Releases, displayed changelogs, SHA-256 verified Windows installer downloads and separate consent before download and installation.
- Automated conversion, settings and GUI tests.

### Changed

- Preset labels use `FORMAT - Description`, such as `MKV - Matroska` and `PPT - PowerPoint`.
- Legacy generated preset names migrate automatically without replacing custom names.
- Repository organized into source, tests, scripts, installer, assets and documentation directories.
- Windows setup defaults to `C:\Programs\Muta Converter`, with an editable destination and administrator privileges.

### Known limitations

- Windows Explorer uses the classic menu; `Not mutable` uses standard text rather than italics.
- LibreOffice, FFmpeg and 7-Zip are external dependencies. iWork import varies by file version; native iWork export is not implemented.
- Native macOS/Linux file-manager integration, code signing and notarization are not implemented.
- Image animations/multiple pages require explicit first-frame extraction; PDF input is not supported.
