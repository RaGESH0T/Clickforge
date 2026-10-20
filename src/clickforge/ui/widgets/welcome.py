"""Dismissible first-run guidance panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clickforge.ui import theme
from clickforge.ui.widgets.common import icon_label


class WelcomeStep(QWidget):
    def __init__(self, number: int, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        number_label = QLabel(str(number))
        number_label.setProperty("role", "stepNumber")
        number_label.setFixedSize(18, 18)
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label = QLabel(text)
        text_label.setProperty("role", "muted")
        text_label.setWordWrap(True)
        layout.addWidget(number_label)
        layout.addWidget(text_label)
        layout.addStretch(1)


class WelcomePanel(QFrame):
    dismissed = Signal()
    preview_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomePanel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 17, 20, 16)
        outer.setSpacing(13)

        top = QHBoxLayout()
        top.setSpacing(12)
        icon_box = QFrame()
        icon_box.setObjectName("LogoMark")
        icon_box.setFixedSize(38, 38)
        icon_layout = QHBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        spark = icon_label("sparkles", theme.ACCENT, 19)
        icon_layout.addWidget(spark, 0, Qt.AlignmentFlag.AlignCenter)
        top.addWidget(icon_box)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        eyebrow = QLabel("FIRST RUN  /  QUICK TOUR")
        eyebrow.setProperty("role", "eyebrow")
        title = QLabel("Built to click. Designed to stop.")
        title.setProperty("role", "panelTitle")
        title.setWordWrap(True)
        body = QLabel(
            "Set a profile, choose where to click, and stay in control. "
            "Clicks are sent only while a session is running."
        )
        body.setProperty("role", "body")
        body.setWordWrap(True)
        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(body)
        top.addLayout(copy, 1)

        self.preview_button = QPushButton("Preview interface")
        self.preview_button.setObjectName("GhostButton")
        self.preview_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_button.setAccessibleName("Open harmless interface preview")
        self.preview_button.clicked.connect(self.preview_requested)
        self.dismiss_button = QPushButton("Got it")
        self.dismiss_button.setObjectName("PrimaryAction")
        self.dismiss_button.setFixedHeight(34)
        self.dismiss_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_button.setAccessibleName("Dismiss welcome panel")
        self.dismiss_button.clicked.connect(self._dismiss)
        top.addWidget(self.preview_button, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.dismiss_button, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(top)

        steps = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        steps.setContentsMargins(50, 0, 0, 0)
        steps.setSpacing(24)
        steps.addWidget(WelcomeStep(1, "Set timing and click profile"), 1)
        steps.addWidget(WelcomeStep(2, "Follow the pointer or pick a point"), 1)
        steps.addWidget(WelcomeStep(3, "Start with F6. Stop instantly with Esc."), 1)
        outer.addLayout(steps)
        self.steps = steps

        hotkey_note = QLabel(
            "Esc stops a running session globally. No account or administrator rights required."
        )
        hotkey_note.setProperty("role", "faint")
        hotkey_note.setWordWrap(True)
        outer.addWidget(hotkey_note)
        self.setAccessibleName("Welcome and quick tour")

    def set_compact(self, compact: bool) -> None:
        if compact:
            self.steps.setDirection(QBoxLayout.Direction.TopToBottom)
            self.steps.setContentsMargins(0, 0, 0, 0)
            self.steps.setSpacing(8)
        else:
            self.steps.setDirection(QBoxLayout.Direction.LeftToRight)
            self.steps.setContentsMargins(50, 0, 0, 0)
            self.steps.setSpacing(24)

    def _dismiss(self) -> None:
        self.dismissed.emit()
