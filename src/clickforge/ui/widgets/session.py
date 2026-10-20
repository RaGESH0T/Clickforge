"""Primary session control card."""

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

from clickforge.backends.capabilities import BackendCapabilities
from clickforge.core.formatting import (
    format_action,
    format_interval,
    format_repeat,
    format_target,
)
from clickforge.core.models import ClickProfile, SessionState
from clickforge.ui import theme
from clickforge.ui.icons import make_icon
from clickforge.ui.widgets.common import (
    Badge,
    KeyCap,
    SummaryItem,
    divider,
    set_role,
)

_STATE_COPY: dict[SessionState, tuple[str, str]] = {
    SessionState.IDLE: (
        "Ready when you are.",
        "No clicks are being sent. Review your profile, then start when you're ready.",
    ),
    SessionState.READY: (
        "Ready to start.",
        "Your profile is set. Press F6 or Start clicking to begin.",
    ),
    SessionState.RUNNING: (
        "Session in progress.",
        "Clicks are running. Stop immediately with Esc or the Stop button.",
    ),
    SessionState.PAUSED: (
        "Session paused.",
        "The worker is paused. Resume or stop from the controls.",
    ),
    SessionState.STOPPING: (
        "Stopping safely.",
        "Waiting for the current repeat to finish, then releasing input.",
    ),
    SessionState.COMPLETED: (
        "Session complete.",
        "The requested repeat count was reached. Your profile is ready to reuse.",
    ),
    SessionState.ERROR: (
        "Session stopped with an error.",
        "Read the message below, then adjust the profile or backend and try again.",
    ),
}


class SessionPanel(QFrame):
    start_requested = Signal()
    stop_requested = Signal()
    preview_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._engine_available = False
        self._engine_reason = ""
        self._start_blocked_reason = ""
        self._state = SessionState.IDLE
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(13)

        top = QHBoxLayout()
        top.setSpacing(8)
        eyebrow = QLabel("SESSION CONTROL")
        eyebrow.setProperty("role", "eyebrow")
        top.addWidget(eyebrow)
        top.addStretch(1)
        self.backend_badge = Badge("INPUT CHECKING")
        self.backend_badge.setAccessibleName("Input backend status")
        top.addWidget(self.backend_badge)
        layout.addLayout(top)

        main = QHBoxLayout()
        main.setSpacing(24)
        copy = QVBoxLayout()
        copy.setSpacing(6)
        self.state_title = QLabel(_STATE_COPY[SessionState.IDLE][0])
        self.state_title.setProperty("role", "hero")
        self.state_title.setAccessibleName("Session status")
        self.state_subtitle = QLabel(_STATE_COPY[SessionState.IDLE][1])
        self.state_subtitle.setProperty("role", "body")
        self.state_subtitle.setWordWrap(True)
        self.state_subtitle.setMaximumWidth(500)
        copy.addWidget(self.state_title)
        copy.addWidget(self.state_subtitle)
        copy.addStretch(1)
        main.addLayout(copy, 1)

        controls = QVBoxLayout()
        controls.setSpacing(7)
        button_row = QHBoxLayout()
        button_row.setSpacing(9)
        self.start_button = QPushButton("Start clicking")
        self.start_button.setObjectName("PrimaryAction")
        self.start_button.setIcon(make_icon("play", theme.ACCENT_TEXT, 16))
        self.start_button.setIconSize(QSize(16, 16))
        self.start_button.setFixedSize(174, 46)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setAccessibleName("Start clicking session")
        self.start_button.clicked.connect(self.start_requested)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("DangerAction")
        self.stop_button.setIcon(make_icon("square", theme.DANGER, 14, theme.FAINT))
        self.stop_button.setIconSize(QSize(14, 14))
        self.stop_button.setFixedSize(104, 46)
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setAccessibleName("Stop session")
        self.stop_button.clicked.connect(self.stop_requested)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        controls.addLayout(button_row)

        hints = QHBoxLayout()
        hints.setSpacing(6)
        hints.addWidget(KeyCap("F6"))
        start_hint = QLabel("start / stop")
        start_hint.setProperty("role", "faint")
        hints.addWidget(start_hint)
        hints.addSpacing(5)
        hints.addWidget(KeyCap("Esc"))
        stop_hint = QLabel("emergency stop")
        stop_hint.setProperty("role", "faint")
        hints.addWidget(stop_hint)
        hints.addStretch(1)
        self.preview_button = QPushButton("  Test interface")
        self.preview_button.setObjectName("LinkButton")
        self.preview_button.setIcon(make_icon("keyboard", theme.MUTED, 13))
        self.preview_button.setIconSize(QSize(13, 13))
        self.preview_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_button.setAccessibleName("Test the interface safely")
        self.preview_button.clicked.connect(self.preview_requested)
        hints.addWidget(self.preview_button)
        controls.addLayout(hints)
        main.addLayout(controls, 0)
        layout.addLayout(main)

        strip = QFrame()
        strip.setObjectName("SummaryStrip")
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(16, 7, 16, 7)
        strip_layout.setSpacing(16)
        self.interval_item = SummaryItem("Interval", "100 ms")
        self.target_item = SummaryItem("Target", "Follow pointer")
        self.action_item = SummaryItem("Action", "Left / Single")
        self.repeat_item = SummaryItem("Repeat", "Until stopped")
        for index, item in enumerate(
            (self.interval_item, self.target_item, self.action_item, self.repeat_item)
        ):
            if index:
                strip_layout.addWidget(divider(vertical=True))
            strip_layout.addWidget(item, 1)
        layout.addWidget(strip)

        self.safety_note = QLabel()
        self.safety_note.setProperty("role", "faint")
        self.safety_note.setWordWrap(True)
        layout.addWidget(self.safety_note)
        self._refresh_buttons()

    def set_capabilities(self, capabilities: BackendCapabilities) -> None:
        if capabilities.available and capabilities.session_type == "x11":
            text = "INPUT  /  X11 · XTEST"
        elif capabilities.available and capabilities.session_type == "windows":
            text = "INPUT  /  WIN32 · SENDINPUT"
        elif capabilities.available:
            text = f"INPUT  /  {capabilities.display_name.upper()}"
        else:
            text = "INPUT  /  UNAVAILABLE"
        self.backend_badge.setText(text)
        self.backend_badge.setToolTip(
            capabilities.reason or "\n".join(capabilities.notes) or capabilities.display_name
        )
        self.backend_badge.setAccessibleDescription(
            capabilities.reason or capabilities.display_name
        )

    def set_engine_available(self, available: bool, reason: str = "") -> None:
        self._engine_available = available
        self._engine_reason = reason
        self._refresh_buttons()

    def set_start_blocked(self, reason: str) -> None:
        self._start_blocked_reason = reason
        self._refresh_buttons()

    def set_summary(self, profile: ClickProfile) -> None:
        self.interval_item.set_value(format_interval(profile.interval_ms))
        self.target_item.set_value(format_target(profile))
        self.action_item.set_value(format_action(profile))
        self.repeat_item.set_value(format_repeat(profile))
        if profile.session_limit_enabled:
            self.safety_note.setText(
                f"Safety backstop: this session will stop after "
                f"{profile.session_limit_minutes} minutes."
            )
            set_role(self.safety_note, "faint")
        else:
            self.safety_note.setText(
                "Safety backstop disabled. Keep the Stop button and Esc within reach."
            )
            set_role(self.safety_note, "warning")

    def set_state(self, state: SessionState) -> None:
        self._state = state
        title, subtitle = _STATE_COPY[state]
        self.state_title.setText(title)
        self.state_subtitle.setText(subtitle)
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        can_start = (
            self._engine_available
            and not self._start_blocked_reason
            and self._state
            in {
                SessionState.IDLE,
                SessionState.READY,
                SessionState.COMPLETED,
                SessionState.ERROR,
            }
        )
        can_stop = self._state in {SessionState.RUNNING, SessionState.PAUSED}
        self.start_button.setEnabled(can_start)
        self.stop_button.setEnabled(can_stop)
        if not self._engine_available:
            tooltip = self._engine_reason or "Synthetic input is unavailable in this session."
        elif self._start_blocked_reason:
            tooltip = self._start_blocked_reason
        else:
            tooltip = "Start clicking (F6)"
        self.start_button.setToolTip(tooltip)

    @property
    def state(self) -> SessionState:
        return self._state
