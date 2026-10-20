#!/usr/bin/env python3
"""Render documentation screenshots without touching real user settings."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from clickforge.backends.capabilities import detect_capabilities  # noqa: E402
from clickforge.services.first_run import FirstRunStore  # noqa: E402
from clickforge.ui.dialogs.preview import PreviewDialog  # noqa: E402
from clickforge.ui.dialogs.settings import SettingsDialog  # noqa: E402
from clickforge.ui.icons import clear_icon_cache  # noqa: E402
from clickforge.ui.main_window import MainWindow  # noqa: E402
from clickforge.ui.theme import apply_theme  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"


def _pump(app: QApplication) -> None:
    for _ in range(4):
        app.processEvents()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication([sys.argv[0]])
    apply_theme(app)
    store = FirstRunStore(Path(tempfile.mkdtemp(prefix="clickforge-shots-")) / "ui-state.json")
    capabilities = detect_capabilities()

    window = MainWindow(capabilities=capabilities, first_run_store=store, show_welcome=False)
    window.resize(1200, 900)
    window.show()
    _pump(app)
    window.grab().save(str(OUT / "main-window.png"))
    window.welcome_panel.setVisible(True)
    window.resize(1200, 1000)
    _pump(app)
    window.welcome_panel.grab().save(str(OUT / "welcome-panel.png"))
    window.close()

    preview = PreviewDialog()
    preview.resize(680, 650)
    preview.show()
    preview.set_state(preview.current_state)
    _pump(app)
    preview.grab().save(str(OUT / "interface-preview.png"))
    preview.close()

    settings = SettingsDialog(capabilities)
    settings.resize(720, 620)
    settings.show()
    _pump(app)
    settings.grab().save(str(OUT / "settings.png"))
    settings.close()

    preview.deleteLater()
    settings.deleteLater()
    _pump(app)
    clear_icon_cache()
    print(f"Screenshots written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
