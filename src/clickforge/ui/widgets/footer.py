"""Application footer with version and privacy note."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from clickforge import __milestone__, __version__
from clickforge.ui import theme
from clickforge.ui.widgets.common import icon_label


class FooterBar(QFrame):
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
