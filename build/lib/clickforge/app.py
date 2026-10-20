"""Application entry point."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from clickforge import (
    __app_name__,
    __app_slug__,
    __app_vendor__,
    __version__,
)
from clickforge.backends.capabilities import detect_capabilities
from clickforge.services.first_run import FirstRunStore
from clickforge.services.logging_setup import configure_logging
from clickforge.services.paths import log_file
from clickforge.ui.icons import app_icon, clear_icon_cache
from clickforge.ui.main_window import MainWindow
from clickforge.ui.theme import apply_theme

LOG = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clickforge",
        description="ClickForge - a safety-first desktop autoclicker.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--show-welcome",
        action="store_true",
        help="show the first-run welcome panel even if it was already dismissed",
    )
    parser.add_argument(
        "--skip-welcome",
        action="store_true",
        help="hide the first-run welcome panel for this launch",
    )
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    return parser


def _install_excepthook() -> None:
    def hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        LOG.critical("Unhandled exception\n%s", details)
        app = QApplication.instance()
        if app is not None:
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("ClickForge")
            box.setText("ClickForge hit an unexpected error.")
            box.setInformativeText(
                "No session was left running. A technical detail was written to the local log.\n\n"
                f"Log: {log_file()}"
            )
            box.setDetailedText(details)
            box.exec()

    sys.excepthook = hook


def build_application(argv: list[str]) -> QApplication:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QGuiApplication.setDesktopFileName(__app_slug__)
    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__app_vendor__)
    app.setDesktopFileName(__app_slug__)
    app.setWindowIcon(app_icon())
    apply_theme(app)
    app.aboutToQuit.connect(clear_icon_cache)
    return app


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    log_path = configure_logging(verbose=args.verbose)
    _install_excepthook()
    LOG.info("Starting %s %s", __app_name__, __version__)
    LOG.info("Log file: %s", log_path)

    app = build_application([sys.argv[0]])
    capabilities = detect_capabilities()
    LOG.info(
        "Backend: %s (%s), session=%s",
        capabilities.display_name,
        capabilities.status_label,
        capabilities.session_type,
    )

    store = FirstRunStore()
    show_welcome: bool | None
    if args.skip_welcome:
        show_welcome = False
    elif args.show_welcome:
        show_welcome = True
    else:
        show_welcome = None

    window = MainWindow(
        capabilities=capabilities,
        first_run_store=store,
        show_welcome=show_welcome,
    )
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    if not window.start_global_hotkeys():
        LOG.info("Global emergency stop is unavailable; local Esc still works")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
