# Changelog

All notable changes are recorded here. Versions follow Semantic Versioning.

## [Unreleased]

## [0.1.8] - 2026-11-26

### Fixed

- Render nested SVG viewports with bundled resvg, fixing completely transparent PNGs from QR-code SVG exports.
- Preserve nested positioning, viewBox scaling and clipping together with user-selected dimensions, rotation and print DPI.

## [0.1.7] - 2026-11-26

### Added

- Ask for width, height, aspect-ratio locking and print resolution before each SVG raster conversion from Explorer or Preferences; cancelling creates no files.
- Apply the selected pixel dimensions after rotation and store DPI in PNG, JPG, TIFF, BMP and PDF outputs; show print-size estimates and format-specific limitations.
- Add `--width`, `--height` and `--dpi` to non-interactive SVG conversion commands.

## [0.1.6] - 2026-11-26

### Changed

- Always install or refresh the Windows context menu, including upgrades from installations that previously left the option unchecked; remove the installer checkbox.
- Remove the menu-removal button from Preferences. Context-menu cleanup still runs during uninstallation.

## [0.1.5] - 2026-11-26

### Added

- Convert SVG files to PNG, JPG, WebP, AVIF, GIF, BMP, TIFF, ICO and raster PDF using bundled Qt SVG rendering.
- Trace PNG, JPG and other raster images into real SVG vector paths with bundled VTracer, including color detail, speckle removal and black-and-white settings.
- Add SVG to the context menu and preferences; migrate existing full-input image presets and add the SVG output preset while retaining customized filters, names and options.
- Run SVG rendering and tracing in a separate process with timeout and size limits; reject external SVG resources and require explicit static export for animations.

## [0.1.4] - 2026-11-24

### Changed

- Rename the product to Muta throughout the interface, help, installer, shortcuts, package metadata and release downloads; retain file converter wording in the description.
- Use `C:\Programs\Muta` for new Windows installations and reuse the existing installation directory during upgrades.
- Preserve settings and the installer identity, accept both installer naming schemes in the updater, and publish a legacy installer alias for older clients.

## [0.1.3] - 2026-11-24

### Added

- Credit WoollySheep in the About dialog and Preferences About tab, localized in all five languages.
- Identify WoollySheep as the Windows installer publisher.

## [0.1.2] - 2026-11-24

### Added

- English, French, German, Spanish and Italian translations for the interface, tray menu, conversion messages and update prompts.
- Language selection in Preferences, with localized Qt buttons and dialogs.

### Fixed

- Persist the installer language before creating the context menu or starting Muta; English installations now display `Muta · Convert to`.
- Refresh existing menu entries when the installation or application language changes, while preserving custom preset names and settings.
- Keep the selected application language when launching an update installer.

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
