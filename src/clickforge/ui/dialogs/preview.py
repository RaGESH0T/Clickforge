"""Harmless state and keyboard preview dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from clickforge.core.models import SessionState
from clickforge.ui import theme
from clickforge.ui.widgets.common import Badge, IconButton, StatusPill, icon_label


@dataclass(frozen=True)
class StatePreview:
    title: str
    description: str


_STATE_PREVIEWS: dict[SessionState, StatePreview] = {
    SessionState.IDLE: StatePreview(
        "Ready when you are.",
        "No session is running. Configuration is editable and the start control is available.",
    ),
    SessionState.READY: StatePreview(
        "Ready to start.",
        "The profile passed validation. Start is available and the hotkey hint is visible.",
    ),
    SessionState.RUNNING: StatePreview(
        "Session in progress.",
        "The status indicator pulses, configuration is locked, and emergency stop is prominent.",
    ),
    SessionState.PAUSED: StatePreview(
        "Session paused.",
        "The worker is paused. The UI clearly distinguishes this from a stopped session.",
    ),
    SessionState.STOPPING: StatePreview(
        "Stopping safely.",
        "The worker has been asked to cancel and releases input before reporting stopped.",
    ),
    SessionState.COMPLETED: StatePreview(
        "Session complete.",
        "A finite run reached its requested count and stopped automatically.",
    ),
    SessionState.ERROR: StatePreview(
        "Session stopped with an error.",
        "A plain-language message explains the failure and offers a diagnostic report.",
    ),
}


class KeyCapture(QFrame):
    key_detected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KeyCapture")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("Local keyboard test area")
        self.setAccessibleDescription("Click here, then press F6, F7 or Escape.")
        self.setFixedHeight(122)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)
        eyebrow = QLabel("LOCAL KEY TEST")
        eyebrow.setProperty("role", "eyebrow")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)
        self.key_label = QLabel("—")
        self.key_label.setObjectName("CapturedKey")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.key_label)
        self.status = QLabel("Click here, then press F6, F7 or Esc.")
        self.status.setProperty("role", "faint")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        self.status.setText("Listening for F6, F7 or Esc.")
        layout = self.layout()
        if layout is not None:
            layout.setContentsMargins(16, 12, 16, 12)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        self.status.setText("Click here, then press F6, F7 or Esc.")
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        mapping = {
            Qt.Key.Key_F6: ("F6", "Start / stop key detected locally."),
            Qt.Key.Key_F7: ("F7", "Position-capture key detected locally."),
            Qt.Key.Key_Escape: ("Esc", "Emergency-stop key detected locally."),
        }
        result = mapping.get(event.key())
        if result is None:
            super().keyPressEvent(event)
            return
        key, message = result
        self.key_label.setText(key)
        self.status.setText(f"{message} Global registration is not active in this build.")
        self.key_detected.emit(key)
        event.accept()


class PreviewDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Interface preview")
        self.setModal(True)
        self.resize(680, 650)
        self.setMinimumWidth(620)
        self._state = SessionState.RUNNING
        self._state_buttons: dict[SessionState, QRadioButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(11)
        self._logo = QFrame()
        self._logo.setObjectName("LogoMark")
        self._logo.setFixedSize(38, 38)
        logo_layout = QHBoxLayout(self._logo)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(
            icon_label("sparkles", theme.ACCENT, 19), 0, Qt.AlignmentFlag.AlignCenter
        )
        header.addWidget(self._logo)
        title_copy = QVBoxLayout()
        title_copy.setSpacing(1)
        title = QLabel("Interface preview")
        title.setObjectName("ScreenTitle")
        subtitle = QLabel("A harmless walkthrough. This window never sends clicks.")
        subtitle.setProperty("role", "muted")
        title_copy.addWidget(title)
        title_copy.addWidget(subtitle)
        header.addLayout(title_copy, 1)
        close_button = IconButton("x", "Close interface preview")
        close_button.clicked.connect(self.accept)
        header.addWidget(close_button)
        root.addLayout(header)

        states_label = QLabel("UI STATES")
        states_label.setProperty("role", "eyebrow")
        root.addWidget(states_label)
        state_frame = QFrame()
        state_frame.setObjectName("Segmented")
        state_grid = QGridLayout(state_frame)
        state_grid.setContentsMargins(3, 3, 3, 3)
        state_grid.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        order = [
            SessionState.IDLE,
            SessionState.READY,
            SessionState.RUNNING,
            SessionState.PAUSED,
            SessionState.STOPPING,
            SessionState.COMPLETED,
            SessionState.ERROR,
        ]
        for index, state in enumerate(order):
            button = QRadioButton(state.value.capitalize())
            button.setProperty("segment", True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(30)
            button.setAccessibleName(f"Preview {state.value} state")
            self._group.addButton(button)
            self._state_buttons[state] = button
            state_grid.addWidget(button, 0, index)
            state_grid.setColumnStretch(index, 1)
            button.toggled.connect(
                lambda checked, s=state: self._on_state_selected(s) if checked else None
            )
        root.addWidget(state_frame)

        self.preview_card = QFrame()
        self.preview_card.setObjectName("PreviewStateCard")
        card_layout = QVBoxLayout(self.preview_card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(8)
        card_header = QHBoxLayout()
        self.status_pill = StatusPill(SessionState.RUNNING)
        card_header.addWidget(self.status_pill)
        card_header.addStretch(1)
        card_header.addWidget(Badge("NO CLICKS SENT", accent=True))
        card_layout.addLayout(card_header)
        self.preview_title = QLabel()
        self.preview_title.setProperty("role", "panelTitle")
        self.preview_description = QLabel()
        self.preview_description.setProperty("role", "body")
        self.preview_description.setWordWrap(True)
        card_layout.addWidget(self.preview_title)
        card_layout.addWidget(self.preview_description)
        root.addWidget(self.preview_card)

        keyboard_label = QLabel("KEYBOARD CHECK")
        keyboard_label.setProperty("role", "eyebrow")
        root.addWidget(keyboard_label)
        self.key_capture = KeyCapture()
        root.addWidget(self.key_capture)
        note = QLabel(
            "This checks local key handling only. It does not register global hotkeys, "
            "move the pointer or send mouse input."
        )
        note.setProperty("role", "faint")
        note.setWordWrap(True)
        root.addWidget(note)

        footer = QHBoxLayout()
        footer.addStretch(1)
        close = QPushButton("Close preview")
        close.setObjectName("GhostButton")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)

        self.set_state(SessionState.RUNNING)
        self.key_capture.setFocus()

    def set_state(self, state: SessionState) -> None:
        button = self._state_buttons[state]
        if not button.isChecked():
            button.setChecked(True)
        self._apply_state(state)

    def _on_state_selected(self, state: SessionState) -> None:
        self._apply_state(state)

    def _apply_state(self, state: SessionState) -> None:
        self._state = state
        preview = _STATE_PREVIEWS[state]
        self.status_pill.set_state(state)
        self.preview_title.setText(preview.title)
        self.preview_description.setText(preview.description)

    @property
    def current_state(self) -> SessionState:
        return self._state

    def showEvent(self, event: QEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.key_capture.setFocus()
