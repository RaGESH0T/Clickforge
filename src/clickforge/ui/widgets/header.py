"""Custom application header with brand and live status."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clickforge import (
    __app_name__,
    __product_name__,
    __product_subtitle__,
    __version__,
)
from clickforge.core.models import SessionState
from clickforge.ui import theme
from clickforge.ui.icons import make_pixmap
from clickforge.ui.widgets.common import Badge, IconButton, StatusPill, divider


class BrandMark(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LogoMark")
        self.setFixedSize(42, 42)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        icon = QLabel()
        icon.setPixmap(make_pixmap("crosshair", theme.ACCENT, 23))
        icon.setFixedSize(23, 23)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)


class AppHeader(QFrame):
    help_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(76)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(13)

        layout.addWidget(BrandMark())

        brand = QVBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(1)
        name = QLabel(__product_name__)
        name.setObjectName("BrandName")
        name.setAccessibleName(__app_name__)
        subtitle = QLabel(__product_subtitle__)
        subtitle.setObjectName("BrandSub")
        sub_font = subtitle.font()
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.2)
        subtitle.setFont(sub_font)
        brand.addWidget(name)
        brand.addWidget(subtitle)
        layout.addLayout(brand)

        version = QLabel(f"v{__version__}")
        version.setObjectName("VersionLabel")
        layout.addWidget(version, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(Badge("LOCAL ENGINE"), 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        self.status_pill = StatusPill()
        self.status_pill.setAccessibleName("Application status")
        layout.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(divider(vertical=True))
        self.help_button = IconButton("circle-help", "Open help and interface preview")
        self.settings_button = IconButton("settings", "Open settings")
        self.help_button.clicked.connect(self.help_requested)
        self.settings_button.clicked.connect(self.settings_requested)
        layout.addWidget(self.help_button)
        layout.addWidget(self.settings_button)

    def set_state(self, state: SessionState) -> None:
        self.status_pill.set_state(state)

    @property
    def status(self) -> StatusPill:
        return self.status_pill
