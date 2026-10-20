"""Global hotkey reference panel."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clickforge.ui import theme
from clickforge.ui.icons import make_icon
from clickforge.ui.widgets.common import Badge, KeyCap


class HotkeyRow(QWidget):
    def __init__(
        self,
        action: str,
        shortcut: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        title = QLabel(action)
        title.setProperty("role", "summaryStrong")
        copy.addWidget(title)
        if hint:
            subtitle = QLabel(hint)
            subtitle.setProperty("role", "faint")
            subtitle.setWordWrap(True)
            copy.addWidget(subtitle)
        layout.addLayout(copy, 1)
        layout.addWidget(KeyCap(shortcut), 0, Qt.AlignmentFlag.AlignVCenter)


class HotkeysPanel(QFrame):
    test_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAccessibleName("Global hotkey reference")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        header = QHBoxLayout()
        eyebrow = QLabel("GLOBAL HOTKEYS")
        eyebrow.setProperty("role", "eyebrow")
        header.addWidget(eyebrow)
        header.addStretch(1)
        header.addWidget(Badge("DEFAULT"))
        layout.addLayout(header)

        layout.addWidget(HotkeyRow("Start / stop", "F6", "Toggle while this window is focused"))
        layout.addWidget(HotkeyRow("Capture position", "F7", "Set a fixed click point"))
        layout.addWidget(HotkeyRow("Emergency stop", "Esc", "Global while a session is running"))

        note = QLabel("Esc is reserved only during an active session.")
        note.setProperty("role", "faint")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.test_button = QPushButton("  Test keyboard")
        self.test_button.setObjectName("LinkButton")
        self.test_button.setIcon(make_icon("keyboard", theme.MUTED, 13))
        self.test_button.setIconSize(QSize(13, 13))
        self.test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_button.setAccessibleName("Test local keyboard handling")
        self.test_button.clicked.connect(self.test_requested)
        layout.addWidget(self.test_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)


class HotkeySummaryRow(HotkeyRow):
    pass
