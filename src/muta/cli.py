from __future__ import annotations

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
    root = argparse.ArgumentParser(prog="muta", description="Muta Converter — conversioni locali")
    root.add_argument("--version", action="version", version=f"Muta Converter {__version__}")
    root.add_argument("--tray", action="store_true", help="Avvia nella systray")
    root.add_argument("--preferences", action="store_true", help="Apri Preferences")
    sub = root.add_subparsers(dest="command")
    conversion = sub.add_parser("convert", help="Converti uno o più file")
    choice = conversion.add_mutually_exclusive_group(required=True)
    choice.add_argument("--to", "-t", dest="target")
    choice.add_argument("--preset")
    conversion.add_argument("--output-dir", type=Path)
    conversion.add_argument("--quality", type=int)
    conversion.add_argument("--first-frame", action="store_true", default=None)
    conversion.add_argument("--notify", action="store_true", help="Mostra avanzamento e risultato in una finestra")
    conversion.add_argument("files", nargs="+", type=Path)
    formats = sub.add_parser("formats", help="Formati attualmente disponibili")
    formats.add_argument("file", type=Path)
    sub.add_parser("doctor", help="Verifica motori di conversione")
    unavailable = sub.add_parser("not-mutable", help="Spiega perché non ci sono conversioni")
    unavailable.add_argument("file", type=Path)
    shell = sub.add_parser("shell", help="Gestisci menu Windows")
    shell.add_argument("action", choices=["install", "remove"])
    startup = sub.add_parser("autostart", help="Avvio automatico su Windows")
    startup.add_argument("action", choices=["enable", "disable"])
    sub.add_parser("uninstall-integration", help="Rimuovi menu e avvio automatico")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command is None:
            from .gui import main as gui_main
            return gui_main(show_preferences=args.preferences or not args.tray)
        if args.command == "uninstall-integration":
            from .integration import remove_menu, set_autostart
            remove_menu()
            set_autostart(False)
            return 0
        if args.command == "not-mutable":
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication([])
            QMessageBox.information(None, "Muta · Not mutable",
                f"Nessuna conversione disponibile per {args.file.name}.\n\n"
                "Controlla i preset e i motori installati nelle Preferences.")
            return 0
        settings = load_settings()
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
                        raise ConversionError(f"Il preset non accetta {source.suffix}.")
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
            app = QApplication.instance() or QApplication([])
            QMessageBox.critical(None, "Muta Converter", str(exc))
        else:
            print(str(exc), file=sys.stderr)
        return 1
