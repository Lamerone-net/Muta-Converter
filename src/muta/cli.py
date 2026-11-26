from __future__ import annotations
from .i18n import tr, set_language, normalize_language, LANGUAGES, INSTALLER_LANGUAGES, application

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

from .engines import ConversionError, diagnostics
from . import __version__
from .service import Options, convert, targets_for
from .settings import load_settings, save_settings


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="muta", description=tr('Muta — convertitore di file locale'))
    root.add_argument("--version", action="version", version=f"Muta {__version__}")
    root.add_argument("--tray", action="store_true", help=tr('Avvia nella systray'))
    root.add_argument("--preferences", action="store_true", help=tr('Apri Preferences'))
    sub = root.add_subparsers(dest="command")
    conversion = sub.add_parser("convert", help=tr('Converti uno o più file'))
    choice = conversion.add_mutually_exclusive_group(required=True)
    choice.add_argument("--to", "-t", dest="target")
    choice.add_argument("--preset")
    conversion.add_argument("--output-dir", type=Path)
    conversion.add_argument("--quality", type=int)
    conversion.add_argument("--first-frame", action="store_true", default=None)
    conversion.add_argument("--notify", action="store_true", help=tr('Mostra avanzamento e risultato in una finestra'))
    conversion.add_argument("files", nargs="+", type=Path)
    formats = sub.add_parser("formats", help=tr('Formati attualmente disponibili'))
    formats.add_argument("file", type=Path)
    sub.add_parser("doctor", help=tr('Verifica motori di conversione'))
    unavailable = sub.add_parser("not-mutable", help=tr('Spiega perché non ci sono conversioni'))
    unavailable.add_argument("file", type=Path)
    shell = sub.add_parser("shell", help=tr('Gestisci menu Windows'))
    shell.add_argument("action", choices=["install", "remove"])
    startup = sub.add_parser("autostart", help=tr('Avvio automatico su Windows'))
    startup.add_argument("action", choices=["enable", "disable"])
    sub.add_parser("uninstall-integration", help=tr('Rimuovi menu e avvio automatico'))
    configure = sub.add_parser("configure", help=tr('Imposta la lingua dell’app'))
    configure.add_argument("--language", required=True, choices=[*LANGUAGES, *INSTALLER_LANGUAGES])
    return root


def main(argv=None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if len(raw) == 2 and raw[0] == "_svg-worker":
        from .svg import worker
        return worker(Path(raw[1]))
    args = None
    try:
        # Uninstall must still work if the user's preferences are damaged.
        if (sys.argv[1:] if argv is None else argv) == ["uninstall-integration"]:
            from .integration import remove_menu, set_autostart
            remove_menu()
            set_autostart(False)
            return 0
        settings = load_settings()
        set_language(settings.language)
        args = parser().parse_args(argv)
        if args.command == "configure":
            from .integration import menu_installed, install_menu
            settings.language = normalize_language(args.language)
            save_settings(settings)
            set_language(settings.language)
            if menu_installed():
                install_menu(settings)
            return 0
        if args.command is None:
            from .gui import main as gui_main
            return gui_main(show_preferences=args.preferences or not args.tray)
        if args.command == "not-mutable":
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = application()
            QMessageBox.information(None, tr('Muta · Not mutable'),
                tr('Nessuna conversione disponibile per {0}.\n\nControlla i preset e i motori installati nelle Preferences.', args.file.name))
            return 0
        settings.apply_engines()
        if args.command == "doctor":
            print(json.dumps(diagnostics(), indent=2, ensure_ascii=False))
        elif args.command == "formats":
            print(" ".join(targets_for(args.file)))
        elif args.command == "shell":
            from .integration import install_menu, remove_menu
            install_menu(settings) if args.action == "install" else remove_menu()
        elif args.command == "autostart":
            from .integration import set_autostart
            settings.autostart = args.action == "enable"
            set_autostart(settings.autostart)
            save_settings(settings)
        elif args.command == "convert":
            options = Options()
            if args.preset:
                preset = settings.preset(args.preset)
                options, target = preset.options, preset.target
                for source in args.files:
                    if source.suffix.lower().lstrip(".") not in preset.inputs:
                        raise ConversionError(tr('Il preset non accetta {0}.', source.suffix))
            else:
                target = args.target
            if args.quality is not None:
                options = replace(options, quality=args.quality)
            if args.first_frame is not None:
                options = replace(options, first_frame=args.first_frame)
            output_dir = args.output_dir or (Path(settings.output_dir) if settings.output_dir else None)
            if args.notify:
                from .gui import run_conversion
                return run_conversion(args.files, target, options, output_dir)
            failed = False
            for source in args.files:
                try:
                    print(convert(source, target, output_dir, options))
                except ConversionError as exc:
                    failed = True
                    print(f"{source}: {exc}", file=sys.stderr)
            return 1 if failed else 0
        return 0
    except (ConversionError, OSError) as exc:
        if getattr(args, "notify", False) or sys.stderr is None:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = application()
            QMessageBox.critical(None, "Muta", str(exc))
        else:
            print(str(exc), file=sys.stderr)
        return 1
