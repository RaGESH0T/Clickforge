"""Settings, privacy and diagnostic dialog."""

from __future__ import annotations

import contextlib
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from clickforge import __license__, __milestone__, __version__
from clickforge.backends.capabilities import BackendCapabilities
from clickforge.services.diagnostics import build_diagnostics
from clickforge.services.paths import config_dir, log_dir
from clickforge.ui import theme
from clickforge.ui.icons import make_icon
from clickforge.ui.widgets.common import (
    Badge,
    SectionTitle,
    divider,
    icon_label,
)
from clickforge.ui.widgets.hotkeys import HotkeyRow


class SettingsDialog(QDialog):
    welcome_requested = Signal()
    preview_requested = Signal()

    def __init__(
        self,
        capabilities: BackendCapabilities,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._capabilities = capabilities
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(720, 620)
        self.setMinimumSize(660, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(11)
        self._logo = QFrame()
        self._logo.setObjectName("LogoMark")
        self._logo.setFixedSize(38, 38)
        logo_layout = QHBoxLayout(self._logo)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(
            icon_label("sliders-horizontal", theme.ACCENT, 19),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        header.addWidget(self._logo)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        title = QLabel("Settings")
        title.setObjectName("ScreenTitle")
        subtitle = QLabel("Local preferences, shortcuts and support information.")
        subtitle.setProperty("role", "muted")
        copy.addWidget(title)
        copy.addWidget(subtitle)
        header.addLayout(copy, 1)
        header.addWidget(Badge("LOCAL ENGINE"))
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        self.tabs.addTab(self._build_data_tab(), "Data privacy")
        self.tabs.addTab(self._build_about_tab(), "About")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setProperty("role", "faint")
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        close = QPushButton("Close")
        close.setObjectName("GhostButton")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)

    def _page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(11)
        return page, layout

    def _build_general_tab(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(SectionTitle("sparkles", "First-run guidance", "Replay the quick tour"))
        row = QHBoxLayout()
        copy = QLabel(
            "Show the welcome panel again to review controls, default shortcuts and "
            "the emergency stop."
        )
        copy.setProperty("role", "muted")
        copy.setWordWrap(True)
        row.addWidget(copy, 1)
        show_welcome = QPushButton("Show welcome panel")
        show_welcome.setObjectName("GhostButton")
        show_welcome.setCursor(Qt.CursorShape.PointingHandCursor)
        show_welcome.clicked.connect(self._request_welcome)
        row.addWidget(show_welcome, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row)
        layout.addWidget(divider())

        layout.addWidget(SectionTitle("shield-check", "Safety defaults", "Built-in backstop"))
        safety = QLabel(
            "Sessions default to a 30-minute automatic stop. Timing, repeat counts and "
            "safety controls are available on the main screen."
        )
        safety.setProperty("role", "muted")
        safety.setWordWrap(True)
        layout.addWidget(safety)
        layout.addWidget(divider())

        layout.addWidget(SectionTitle("terminal", "Input backend", "Detected locally"))
        backend_card = QFrame()
        backend_card.setObjectName("InlineNote")
        backend_layout = QVBoxLayout(backend_card)
        backend_layout.setContentsMargins(14, 12, 14, 12)
        backend_layout.setSpacing(3)
        name = QLabel(self._capabilities.display_name)
        name.setProperty("role", "summaryStrong")
        detail = QLabel(
            f"Session: {self._capabilities.session_type}  ·  Status: "
            f"{self._capabilities.status_label}"
        )
        detail.setProperty("role", "faint")
        backend_layout.addWidget(name)
        backend_layout.addWidget(detail)
        if self._capabilities.reason:
            reason = QLabel(self._capabilities.reason)
            reason.setProperty("role", "warning")
            reason.setWordWrap(True)
            backend_layout.addWidget(reason)
        for note in self._capabilities.notes:
            note_label = QLabel(f"· {note}")
            note_label.setProperty("role", "faint")
            note_label.setWordWrap(True)
            backend_layout.addWidget(note_label)
        layout.addWidget(backend_card)
        layout.addStretch(1)
        return page

    def _build_hotkeys_tab(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(SectionTitle("key-round", "Default shortcuts", "Global when supported"))
        layout.addWidget(HotkeyRow("Start / stop", "F6", "Toggle while the window is focused"))
        layout.addWidget(HotkeyRow("Capture position", "F7", "Pick a fixed click point"))
        layout.addWidget(HotkeyRow("Emergency stop", "Esc", "Global while a session is running"))
        layout.addWidget(divider())
        note = QLabel(
            "Shortcut editing is not available yet. Esc is captured globally only while a "
            "session is running, so it remains usable everywhere else."
        )
        note.setProperty("role", "muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        test = QPushButton("  Test local keyboard")
        test.setObjectName("AccentGhostButton")
        test.setIcon(make_icon("keyboard", theme.ACCENT, 14))
        test.setIconSize(QSize(14, 14))
        test.setCursor(Qt.CursorShape.PointingHandCursor)
        test.clicked.connect(self._request_preview)
        layout.addWidget(test, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(divider())
        linux_note = QLabel(
            "Linux: global shortcuts require an X11 session. Wayland is detected and reported "
            "as unsupported rather than silently failing."
        )
        linux_note.setProperty("role", "faint")
        linux_note.setWordWrap(True)
        layout.addWidget(linux_note)
        layout.addStretch(1)
        return page

    def _build_data_tab(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(SectionTitle("folder-open", "Local data", "Nothing leaves this computer"))
        layout.addLayout(self._path_row("Configuration", config_dir()))
        layout.addLayout(self._path_row("Logs", log_dir()))
        layout.addWidget(divider())
        layout.addWidget(SectionTitle("copy", "Diagnostics", "Redacted support report"))
        copy = QLabel(
            "The report includes the app version, OS, Qt, backend status and local paths. "
            "Your home directory is redacted. It never includes clicks, coordinates or screenshots."
        )
        copy.setProperty("role", "muted")
        copy.setWordWrap(True)
        layout.addWidget(copy)
        copy_button = QPushButton("Copy diagnostic report")
        copy_button.setObjectName("GhostButton")
        copy_button.setIcon(make_icon("copy", theme.MUTED, 14))
        copy_button.setIconSize(QSize(14, 14))
        copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_button.clicked.connect(self._copy_diagnostics)
        layout.addWidget(copy_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(divider())
        privacy = QLabel(
            "Offline by design: no account, network request, telemetry, ads or bundled offers. "
            "ClickForge does not save session histories or individual clicks."
        )
        privacy.setProperty("role", "faint")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        layout.addStretch(1)
        return page

    def _build_about_tab(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(SectionTitle("info", "About", "Open-source desktop utility"))
        name = QLabel("ClickForge")
        name.setProperty("role", "panelTitle")
        layout.addWidget(name)
        version = QLabel(f"Version {__version__}  ·  {__milestone__}  ·  {__license__} License")
        version.setProperty("role", "faint")
        layout.addWidget(version)
        statement = QLabel(
            "A polished, safety-first desktop autoclicker for Windows and Linux X11. "
            "The project is free, open source, and designed to work indefinitely without "
            "accounts, subscriptions or hosted infrastructure."
        )
        statement.setProperty("role", "muted")
        statement.setWordWrap(True)
        layout.addWidget(statement)
        layout.addWidget(divider())
        tagline = QLabel("Precise control. Transparent operation. Zero telemetry.")
        tagline.setProperty("role", "accent")
        layout.addWidget(tagline)
        layout.addStretch(1)
        return page

    def _path_row(self, label: str, path: Path) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(label)
        title.setProperty("role", "fieldLabel")
        value = QLabel(str(path))
        value.setProperty("role", "faint")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        copy.addWidget(title)
        copy.addWidget(value)
        row.addLayout(copy, 1)
        open_button = QPushButton("Open")
        open_button.setObjectName("GhostButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(lambda checked=False, p=path: self._open_path(p))
        row.addWidget(open_button, 0, Qt.AlignmentFlag.AlignBottom)
        return row

    def _open_path(self, path: Path) -> None:
        with contextlib.suppress(OSError):
            path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _copy_diagnostics(self) -> None:
        report = build_diagnostics(self._capabilities)
        QApplication.clipboard().setText(report)
        self.status_label.setText("Diagnostic report copied to the clipboard.")

    def _request_welcome(self) -> None:
        self.welcome_requested.emit()
        self.accept()

    def _request_preview(self) -> None:
        self.preview_requested.emit()
        self.accept()
