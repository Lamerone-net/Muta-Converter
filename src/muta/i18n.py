"""Application translations shared by the GUI, workers, CLI and Explorer."""
from functools import lru_cache
from importlib.resources import files
import json

LANGUAGES = {"en": "English", "fr": "Français", "de": "Deutsch", "es": "Español", "it": "Italiano"}
INSTALLER_LANGUAGES = {"english": "en", "french": "fr", "german": "de", "spanish": "es", "italian": "it"}
_language = "it"  # Preserve the language of settings created before localization.


def normalize_language(language: str) -> str:
    value = INSTALLER_LANGUAGES.get(language, language)
    if value not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    return value


def set_language(language: str) -> None:
    global _language
    _language = normalize_language(language)


def get_language() -> str:
    return _language


@lru_cache(maxsize=5)
def catalog(language: str) -> dict[str, str]:
    return json.loads(files("muta").joinpath("locales", language + ".json").read_text(encoding="utf-8"))


def tr(source: str, *args, language: str | None = None) -> str:
    translated = catalog(language or _language).get(source, source)
    return translated.format(*args) if args else translated


def configure_qt(app) -> None:
    """Translate Qt's standard buttons/dialogs as well as Muta's own text."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    old = getattr(app, "_muta_translator", None)
    if old is not None:
        app.removeTranslator(old)
        old.deleteLater()
    QLocale.setDefault(QLocale(_language))
    translator = QTranslator(app)
    translator.load("qtbase_" + _language, QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    app._muta_translator = translator


def application():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        QApplication.setAttribute(Qt.AA_DontUseNativeDialogs)
        app = QApplication([])
    configure_qt(app)
    return app
