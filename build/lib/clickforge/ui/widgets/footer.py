"""Application footer with version, privacy note and settings access."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from clickforge import __milestone__, __version__
from clickforge.ui import theme
from clickforge.ui.icons import make_icon
from clickforge.ui.widgets.common import icon_label


class FooterBar(QFrame):
    help_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FooterBar")
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(8)

        self.version_label = QLabel(f"v{__version__}")
        self.version_label.setObjectName("VersionLabel")
        self.version_label.setAccessibleName("Application version")
        layout.addWidget(self.version_label)
        separator = QLabel("/")
        separator.setProperty("role", "faint")
        layout.addWidget(separator)
        milestone = QLabel(__milestone__)
        milestone.setProperty("role", "faint")
        layout.addWidget(milestone)
        layout.addStretch(1)

        layout.addWidget(icon_label("shield-check", theme.ACCENT, 13))
        privacy = QLabel("Offline only · No telemetry")
        privacy.setProperty("role", "faint")
        layout.addWidget(privacy)
        layout.addSpacing(8)

        self.help_button = QPushButton("Help")
        self.help_button.setObjectName("LinkButton")
        self.help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_button.setAccessibleName("Open help and welcome panel")
        self.help_button.clicked.connect(self.help_requested)
        layout.addWidget(self.help_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("GhostButton")
        self.settings_button.setIcon(make_icon("settings", theme.MUTED, 14))
        self.settings_button.setIconSize(QSize(14, 14))
        self.settings_button.setFixedHeight(30)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setAccessibleName("Open settings")
        self.settings_button.clicked.connect(self.settings_requested)
        layout.addWidget(self.settings_button)
