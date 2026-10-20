"""Click profile configuration card."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from clickforge.core.formatting import format_interval, format_interval_range
from clickforge.core.models import (
    DEFAULT_PROFILE,
    MAX_JITTER_MS,
    MAX_REPEATS,
    MAX_SESSION_LIMIT_MINUTES,
    MIN_REPEATS,
    MIN_SESSION_LIMIT_MINUTES,
    ClickProfile,
    ClickType,
    MouseButton,
    RepeatMode,
    TargetMode,
)
from clickforge.ui import theme
from clickforge.ui.icons import make_icon
from clickforge.ui.widgets.common import (
    NumberField,
    SectionTitle,
    SegmentedControl,
    ToggleSwitch,
    divider,
    icon_label,
    set_role,
)


class ClickConfigPanel(QFrame):
    profile_changed = Signal(object)

    def __init__(
        self,
        profile: ClickProfile = DEFAULT_PROFILE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAccessibleName("Click profile configuration")
        self._profile = profile
        self._updating = False
        self._position_picker_available = False
        self._preset_buttons: dict[int, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(13)

        header = QHBoxLayout()
        eyebrow = QLabel("CLICK PROFILE")
        eyebrow.setProperty("role", "eyebrow")
        header.addWidget(eyebrow)
        header.addStretch(1)
        hint = QLabel("Changes apply to the next session")
        hint.setProperty("role", "faint")
        header.addWidget(hint)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(7)
        right = QVBoxLayout()
        right.setSpacing(7)

        left.addWidget(SectionTitle("timer", "Timing", "How often each repeat fires"))
        left.addLayout(self._build_interval_row())
        left.addLayout(self._build_presets_row())
        left.addLayout(self._build_interval_summary())
        left.addSpacing(9)
        left.addWidget(SectionTitle("crosshair", "Target", "Where clicks are sent"))
        left.addWidget(self._build_target_control())
        left.addWidget(self._build_target_stack())
        left.addStretch(1)

        right.addWidget(SectionTitle("mouse-pointer-click", "Action", "What each repeat sends"))
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addWidget(self._labeled("MOUSE BUTTON", self._build_mouse_buttons()), 1)
        action_row.addWidget(self._labeled("CLICK TYPE", self._build_click_type()), 1)
        right.addLayout(action_row)
        right.addSpacing(5)
        right.addWidget(SectionTitle("repeat", "Repeat", "When the session ends"))
        right.addWidget(self._build_repeat_mode())
        right.addLayout(self._build_repeat_count())
        right.addSpacing(5)
        right.addWidget(SectionTitle("shield-check", "Safety", "Hard stops and timing variation"))
        right.addWidget(self._build_auto_stop())
        right.addWidget(self._build_jitter())
        right.addWidget(self._build_timing_range())
        right.addStretch(1)

        body.addLayout(left, 1)
        body.addWidget(divider(vertical=True))
        body.addLayout(right, 1)
        layout.addLayout(body)
        self.emergency_note = QLabel(
            "Emergency stop: Esc or Stop. Cancellation is checked before every repeat."
        )
        self.emergency_note.setProperty("role", "faint")
        self.emergency_note.setWordWrap(True)
        layout.addWidget(self.emergency_note)

        self._refresh_interval_view()
        self._refresh_repeat_view()
        self._refresh_target_view()
        self._refresh_safety_view()
        self._sync_preset_buttons()

    def _build_interval_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(9)
        self.hours = NumberField("Hours", minimum=0, maximum=23, value=0, accessible_name="Hours")
        self.minutes = NumberField(
            "Minutes", minimum=0, maximum=59, value=0, accessible_name="Minutes"
        )
        self.seconds = NumberField(
            "Seconds", minimum=0, maximum=59, value=0, accessible_name="Seconds"
        )
        self.milliseconds = NumberField(
            "Milliseconds",
            minimum=0,
            maximum=999,
            value=self._profile.interval_ms % 1000,
            accessible_name="Milliseconds",
        )
        self.hours.spin.setObjectName("interval_hours")
        self.minutes.spin.setObjectName("interval_minutes")
        self.seconds.spin.setObjectName("interval_seconds")
        self.milliseconds.spin.setObjectName("interval_milliseconds")
        for field in (self.hours, self.minutes, self.seconds, self.milliseconds):
            field.value_changed.connect(self._on_interval_changed)
            row.addWidget(field, 1)
        self._load_interval_into_fields(self._profile.interval_ms)
        return row

    def _build_presets_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        label = QLabel("QUICK")
        label.setProperty("role", "fieldLabel")
        row.addWidget(label)
        row.addSpacing(2)
        for milliseconds, text in (
            (50, "50 ms"),
            (100, "100 ms"),
            (250, "250 ms"),
            (500, "500 ms"),
            (1000, "1 s"),
        ):
            button = QPushButton(text)
            button.setObjectName("Chip")
            button.setProperty("active", False)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(f"Set interval to {text}")
            button.setToolTip(f"Set a {text} interval")
            button.clicked.connect(
                lambda checked=False, value=milliseconds: self._set_interval(value)
            )
            self._preset_buttons[milliseconds] = button
            row.addWidget(button)
        row.addStretch(1)
        return row

    def _build_interval_summary(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.interval_summary = QLabel("100 ms")
        self.interval_summary.setProperty("role", "summaryStrong")
        self.interval_summary.setAccessibleName("Interval summary")
        self.rate_summary = QLabel("about 10.0 clicks/sec")
        self.rate_summary.setProperty("role", "summaryMuted")
        dot = icon_label("circle-dot", theme.ACCENT, 10)
        row.addWidget(dot)
        row.addWidget(self.interval_summary)
        row.addWidget(self.rate_summary)
        row.addStretch(1)
        return row

    def _build_target_control(self) -> SegmentedControl:
        self.target_mode = SegmentedControl()
        self.target_mode.setObjectName("target_mode_control")
        self.target_mode.add_segment(TargetMode.CURSOR, "Follow pointer")
        self.target_mode.add_segment(TargetMode.FIXED, "Fixed point")
        self.target_mode.value_changed.connect(self._on_target_mode_changed)
        self.target_mode.set_value(self._profile.target_mode)
        return self.target_mode

    def _build_target_stack(self) -> QStackedWidget:
        self.target_stack = QStackedWidget()
        self.target_stack.setFixedHeight(122)

        cursor_page = QWidget()
        cursor_layout = QVBoxLayout(cursor_page)
        cursor_layout.setContentsMargins(0, 4, 0, 0)
        cursor_note = QFrame()
        cursor_note.setObjectName("InlineNote")
        cursor_note_layout = QHBoxLayout(cursor_note)
        cursor_note_layout.setContentsMargins(12, 10, 12, 10)
        cursor_note_layout.setSpacing(9)
        cursor_note_layout.addWidget(icon_label("mouse-pointer-2", theme.MUTED, 15))
        cursor_copy = QLabel(
            "Clicks use the pointer position at the moment of each repeat. "
            "The app never moves your pointer."
        )
        cursor_copy.setProperty("role", "muted")
        cursor_copy.setWordWrap(True)
        cursor_note_layout.addWidget(cursor_copy, 1)
        cursor_layout.addWidget(cursor_note)
        cursor_layout.addStretch(1)

        fixed_page = QWidget()
        fixed_layout = QVBoxLayout(fixed_page)
        fixed_layout.setContentsMargins(0, 4, 0, 0)
        fixed_layout.setSpacing(7)
        coordinates = QHBoxLayout()
        coordinates.setSpacing(8)
        self.fixed_x = QLineEdit()
        self.fixed_x.setObjectName("fixed_x")
        self.fixed_x.setPlaceholderText("X")
        self.fixed_x.setValidator(QIntValidator(-100_000, 100_000, self))
        self.fixed_x.setFixedWidth(96)
        self.fixed_x.setAccessibleName("Fixed target X coordinate")
        self.fixed_y = QLineEdit()
        self.fixed_y.setObjectName("fixed_y")
        self.fixed_y.setPlaceholderText("Y")
        self.fixed_y.setValidator(QIntValidator(-100_000, 100_000, self))
        self.fixed_y.setFixedWidth(96)
        self.fixed_y.setAccessibleName("Fixed target Y coordinate")
        for line_edit in (self.fixed_x, self.fixed_y):
            line_edit.setFont(theme.mono_font(12))
            line_edit.textChanged.connect(self._on_coordinates_changed)
        coordinates.addWidget(self.fixed_x)
        coordinates.addWidget(self.fixed_y)
        coordinates.addStretch(1)
        fixed_layout.addLayout(coordinates)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.pick_position_button = QPushButton("Pick on screen")
        self.pick_position_button.setObjectName("GhostButton")
        self.pick_position_button.setIcon(make_icon("crosshair", theme.MUTED, 14))
        self.pick_position_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_position_button.setAccessibleName("Pick a fixed screen position")
        self.pick_position_button.setEnabled(False)
        self.pick_position_button.setToolTip("Position picking arrives in Milestone 4.")
        self.clear_position_button = QPushButton("Clear")
        self.clear_position_button.setObjectName("GhostButton")
        self.clear_position_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_position_button.setAccessibleName("Clear fixed position")
        self.clear_position_button.clicked.connect(self._clear_coordinates)
        actions.addWidget(self.pick_position_button)
        actions.addWidget(self.clear_position_button)
        actions.addStretch(1)
        fixed_layout.addLayout(actions)

        self.target_status = QLabel("No fixed point selected")
        self.target_status.setProperty("role", "faint")
        fixed_layout.addWidget(self.target_status)
        self.picker_note = QLabel("Coordinates use the virtual desktop. Negative values are valid.")
        self.picker_note.setProperty("role", "faint")
        self.picker_note.setWordWrap(True)
        fixed_layout.addWidget(self.picker_note)
        fixed_layout.addStretch(1)

        self.target_stack.addWidget(cursor_page)
        self.target_stack.addWidget(fixed_page)
        self._load_coordinates()
        return self.target_stack

    def _build_mouse_buttons(self) -> SegmentedControl:
        self.mouse_buttons = SegmentedControl()
        self.mouse_buttons.setObjectName("mouse_button_control")
        self.mouse_buttons.add_segment(MouseButton.LEFT, "Left")
        self.mouse_buttons.add_segment(MouseButton.RIGHT, "Right")
        self.mouse_buttons.add_segment(MouseButton.MIDDLE, "Middle")
        self.mouse_buttons.value_changed.connect(self._on_mouse_button_changed)
        self.mouse_buttons.set_value(self._profile.mouse_button)
        return self.mouse_buttons

    def _build_click_type(self) -> SegmentedControl:
        self.click_type = SegmentedControl()
        self.click_type.setObjectName("click_type_control")
        self.click_type.add_segment(
            ClickType.SINGLE,
            "Single",
            tooltip="One repeat sends one click event.",
        )
        self.click_type.add_segment(
            ClickType.DOUBLE,
            "Double",
            tooltip="One repeat sends two click events. Counts are shown as clicks.",
        )
        self.click_type.value_changed.connect(self._on_click_type_changed)
        self.click_type.set_value(self._profile.click_type)
        return self.click_type

    def _build_repeat_mode(self) -> SegmentedControl:
        self.repeat_mode = SegmentedControl()
        self.repeat_mode.setObjectName("repeat_mode_control")
        self.repeat_mode.add_segment(RepeatMode.CONTINUOUS, "Until stopped")
        self.repeat_mode.add_segment(RepeatMode.FIXED, "Fixed count")
        self.repeat_mode.value_changed.connect(self._on_repeat_mode_changed)
        self.repeat_mode.set_value(self._profile.repeat_mode)
        return self.repeat_mode

    def _build_repeat_count(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.repeat_count = NumberField(
            "Repeats",
            minimum=MIN_REPEATS,
            maximum=MAX_REPEATS,
            value=self._profile.repeat_count,
            accessible_name="Number of repeats",
        )
        self.repeat_count.setMaximumWidth(160)
        self.repeat_count.spin.setObjectName("repeat_count")
        self.repeat_count.value_changed.connect(self._on_repeat_count_changed)
        row.addWidget(self.repeat_count)
        self.repeat_count_hint = QLabel()
        self.repeat_count_hint.setProperty("role", "muted")
        self.repeat_count_hint.setWordWrap(True)
        row.addWidget(self.repeat_count_hint, 1)
        return row

    def _build_auto_stop(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        self.auto_stop_toggle = ToggleSwitch()
        self.auto_stop_toggle.setAccessibleName("Enable automatic session stop")
        self.auto_stop_toggle.setChecked(self._profile.session_limit_enabled)
        self.auto_stop_toggle.toggled.connect(self._on_auto_stop_toggled)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        label = QLabel("Auto-stop session")
        label.setProperty("role", "summaryStrong")
        hint = QLabel("Safety backstop after a set duration")
        hint.setProperty("role", "faint")
        copy.addWidget(label)
        copy.addWidget(hint)
        row.addWidget(self.auto_stop_toggle)
        row.addLayout(copy)
        row.addStretch(1)
        self.session_limit_minutes = NumberField(
            "Minutes",
            minimum=MIN_SESSION_LIMIT_MINUTES,
            maximum=MAX_SESSION_LIMIT_MINUTES,
            value=self._profile.session_limit_minutes,
            accessible_name="Session auto-stop minutes",
            width=96,
        )
        self.session_limit_minutes.spin.setObjectName("session_limit_minutes")
        self.session_limit_minutes.value_changed.connect(self._on_session_limit_changed)
        row.addWidget(self.session_limit_minutes)
        return container

    def _build_jitter(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        self.jitter_toggle = ToggleSwitch()
        self.jitter_toggle.setAccessibleName("Enable random timing variation")
        self.jitter_toggle.setChecked(self._profile.jitter_enabled)
        self.jitter_toggle.toggled.connect(self._on_jitter_toggled)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        label = QLabel("Random timing variation")
        label.setProperty("role", "summaryStrong")
        hint = QLabel("Vary each wait by a bounded offset")
        hint.setProperty("role", "faint")
        copy.addWidget(label)
        copy.addWidget(hint)
        row.addWidget(self.jitter_toggle)
        row.addLayout(copy)
        row.addStretch(1)
        self.jitter_ms = NumberField(
            "± ms",
            minimum=0,
            maximum=MAX_JITTER_MS,
            value=self._profile.jitter_ms,
            accessible_name="Random timing variation in milliseconds",
            width=96,
        )
        self.jitter_ms.spin.setObjectName("jitter_ms")
        self.jitter_ms.setEnabled(self._profile.jitter_enabled)
        self.jitter_ms.value_changed.connect(self._on_jitter_changed)
        row.addWidget(self.jitter_ms)
        return container

    def _build_timing_range(self) -> QLabel:
        self.timing_range_summary = QLabel()
        self.timing_range_summary.setProperty("role", "faint")
        self.timing_range_summary.setWordWrap(True)
        return self.timing_range_summary

    def _build_emergency_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("InlineNote")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        layout.addWidget(icon_label("shield-check", theme.ACCENT, 17))
        copy = QVBoxLayout()
        copy.setSpacing(1)
        title = QLabel("Emergency stop stays visible")
        title.setProperty("role", "summaryStrong")
        text = QLabel(
            "Press Esc or use Stop. The worker checks cancellation before every repeat "
            "and cannot keep clicking after it reports stopped."
        )
        text.setProperty("role", "faint")
        text.setWordWrap(True)
        copy.addWidget(title)
        copy.addWidget(text)
        layout.addLayout(copy, 1)
        return strip

    def _labeled(self, label: str, control: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        caption = QLabel(label)
        caption.setProperty("role", "fieldLabel")
        layout.addWidget(caption)
        layout.addWidget(control)
        return wrapper

    def profile(self) -> ClickProfile:
        return self._profile

    def set_profile(self, profile: ClickProfile) -> None:
        self._updating = True
        try:
            self._load_interval_into_fields(profile.interval_ms)
            self.mouse_buttons.set_value(profile.mouse_button)
            self.click_type.set_value(profile.click_type)
            self.repeat_mode.set_value(profile.repeat_mode)
            with QSignalBlocker(self.repeat_count.spin):
                self.repeat_count.set_value(profile.repeat_count)
            self.target_mode.set_value(profile.target_mode)
            with QSignalBlocker(self.fixed_x):
                self.fixed_x.setText("" if profile.target_x is None else str(profile.target_x))
            with QSignalBlocker(self.fixed_y):
                self.fixed_y.setText("" if profile.target_y is None else str(profile.target_y))
            with QSignalBlocker(self.auto_stop_toggle):
                self.auto_stop_toggle.setChecked(profile.session_limit_enabled)
            with QSignalBlocker(self.session_limit_minutes.spin):
                self.session_limit_minutes.set_value(profile.session_limit_minutes)
            with QSignalBlocker(self.jitter_toggle):
                self.jitter_toggle.setChecked(profile.jitter_enabled)
            with QSignalBlocker(self.jitter_ms.spin):
                self.jitter_ms.set_value(profile.jitter_ms)
            self._profile = profile
            self._refresh_interval_view()
            self._refresh_repeat_view()
            self._refresh_target_view()
            self._refresh_safety_view()
            self._sync_preset_buttons()
        finally:
            self._updating = False
        self.profile_changed.emit(self._profile)

    def set_position_picker_available(self, available: bool, reason: str = "") -> None:
        self._position_picker_available = available
        self.pick_position_button.setEnabled(available)
        self.pick_position_button.setToolTip(
            "" if available else (reason or "Screen position capture is unavailable.")
        )
        if not available:
            self.picker_note.setText(
                reason or "Screen position capture is unavailable in this build."
            )

    def _load_interval_into_fields(self, milliseconds: int) -> None:
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, millis = divmod(remainder, 1_000)
        was_updating = self._updating
        self._updating = True
        try:
            self.hours.set_value(hours)
            self.minutes.set_value(minutes)
            self.seconds.set_value(seconds)
            self.milliseconds.set_value(millis)
        finally:
            self._updating = was_updating

    def _current_interval_ms(self) -> int:
        return (
            self.hours.value() * 3_600_000
            + self.minutes.value() * 60_000
            + self.seconds.value() * 1_000
            + self.milliseconds.value()
        )

    def _on_interval_changed(self, value: int) -> None:
        if self._updating:
            return
        interval = self._current_interval_ms()
        self._profile = replace(self._profile, interval_ms=interval)
        self._refresh_interval_view()
        self._sync_preset_buttons()
        self._emit_profile()

    def _set_interval(self, milliseconds: int) -> None:
        self._load_interval_into_fields(milliseconds)
        self._profile = replace(self._profile, interval_ms=milliseconds)
        self._refresh_interval_view()
        self._sync_preset_buttons()
        self._emit_profile()

    def _refresh_interval_view(self) -> None:
        interval = self._profile.interval_ms
        if interval < 1:
            self.interval_summary.setText("Invalid interval")
            self.rate_summary.setText("minimum 1 ms")
            set_role(self.interval_summary, "warning")
            return
        set_role(self.interval_summary, "summaryStrong")
        self.interval_summary.setText(format_interval(interval))
        rate = self._profile.estimated_clicks_per_second
        if self._profile.clicks_per_repeat > 1:
            repeats = 1000.0 / interval
            self.rate_summary.setText(f"≈ {rate:.1f} clicks/sec ({repeats:.1f} repeats/sec)")
        else:
            self.rate_summary.setText(f"≈ {rate:.1f} clicks/sec")

    def _refresh_repeat_view(self) -> None:
        fixed = self._profile.repeat_mode is RepeatMode.FIXED
        self.repeat_count.setEnabled(fixed)
        self.repeat_count.setToolTip("" if fixed else "Switch to Fixed count to edit this value.")
        if not fixed:
            self.repeat_count_hint.setText("Runs until you stop it or the safety timer fires.")
            return
        total = self._profile.total_planned_clicks or 0
        if self._profile.clicks_per_repeat > 1:
            self.repeat_count_hint.setText(
                f"Stops after {self._profile.repeat_count:,} repeats ({total:,} completed clicks)."
            )
        else:
            self.repeat_count_hint.setText(
                f"Stops after {self._profile.repeat_count:,} completed clicks."
            )

    def _refresh_target_view(self) -> None:
        fixed = self._profile.target_mode is TargetMode.FIXED
        self.target_stack.setCurrentIndex(1 if fixed else 0)
        if not fixed:
            self.target_status.setText("Using the live pointer position")
            return
        if self._profile.target_x is None or self._profile.target_y is None:
            self.target_status.setText("No fixed point selected")
            self.target_status.setProperty("role", "faint")
        else:
            self.target_status.setText(
                f"Fixed point: {self._profile.target_x:,}, {self._profile.target_y:,}"
            )
            self.target_status.setProperty("role", "accent")
        self.target_status.style().unpolish(self.target_status)
        self.target_status.style().polish(self.target_status)
        has_coordinates = bool(self.fixed_x.text().strip() or self.fixed_y.text().strip())
        self.clear_position_button.setEnabled(has_coordinates)

    def _refresh_safety_view(self) -> None:
        self.session_limit_minutes.setEnabled(self._profile.session_limit_enabled)
        self.jitter_ms.setEnabled(self._profile.jitter_enabled)
        if not self._profile.jitter_enabled:
            self.timing_range_summary.setText(
                "Fixed waits. Enable variation to add a bounded random offset."
            )
            set_role(self.timing_range_summary, "faint")
            return
        low, high = self._profile.timing_range_ms
        if self._profile.jitter_ms >= self._profile.interval_ms:
            self.timing_range_summary.setText(
                "Variation is larger than the interval and will be clamped. "
                "Use this for user-controlled timing variation only."
            )
            set_role(self.timing_range_summary, "warning")
            return
        set_role(self.timing_range_summary, "faint")
        self.timing_range_summary.setText(
            f"Each wait: {format_interval_range(low, high)}. "
            "For user-controlled timing variation only."
        )

    def _sync_preset_buttons(self) -> None:
        for milliseconds, button in self._preset_buttons.items():
            active = milliseconds == self._profile.interval_ms
            if button.property("active") != active:
                button.setProperty("active", active)
                button.style().unpolish(button)
                button.style().polish(button)

    def _on_mouse_button_changed(self, value: MouseButton) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, mouse_button=value)
        self._emit_profile()

    def _on_click_type_changed(self, value: ClickType) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, click_type=value)
        self._refresh_repeat_view()
        self._refresh_interval_view()
        self._emit_profile()

    def _on_repeat_mode_changed(self, value: RepeatMode) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, repeat_mode=value)
        self._refresh_repeat_view()
        self._emit_profile()

    def _on_repeat_count_changed(self, value: int) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, repeat_count=value)
        self._refresh_repeat_view()
        self._emit_profile()

    def _on_target_mode_changed(self, value: TargetMode) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, target_mode=value)
        self._refresh_target_view()
        self._emit_profile()

    def _on_coordinates_changed(self, _text: str) -> None:
        if self._updating:
            return
        x_text = self.fixed_x.text().strip()
        y_text = self.fixed_y.text().strip()
        x = int(x_text) if x_text not in {"", "-"} else None
        y = int(y_text) if y_text not in {"", "-"} else None
        self._profile = replace(self._profile, target_x=x, target_y=y)
        self._refresh_target_view()
        self._emit_profile()

    def set_target_position(self, x: int, y: int) -> None:
        """Switch to a fixed target and fill in the captured coordinates."""
        self._updating = True
        try:
            self.fixed_x.setText(str(x))
            self.fixed_y.setText(str(y))
            self.target_mode.set_value(TargetMode.FIXED)
        finally:
            self._updating = False
        self._profile = replace(
            self._profile,
            target_mode=TargetMode.FIXED,
            target_x=x,
            target_y=y,
        )
        self._refresh_target_view()
        self._emit_profile()

    def _clear_coordinates(self) -> None:
        self._updating = True
        try:
            self.fixed_x.clear()
            self.fixed_y.clear()
        finally:
            self._updating = False
        self._profile = replace(self._profile, target_x=None, target_y=None)
        self._refresh_target_view()
        self._emit_profile()

    def _on_auto_stop_toggled(self, enabled: bool) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, session_limit_enabled=enabled)
        self._refresh_safety_view()
        self._emit_profile()

    def _on_session_limit_changed(self, minutes: int) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, session_limit_minutes=minutes)
        self._emit_profile()

    def _on_jitter_toggled(self, enabled: bool) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, jitter_enabled=enabled)
        self._refresh_safety_view()
        self._emit_profile()

    def _on_jitter_changed(self, milliseconds: int) -> None:
        if self._updating:
            return
        self._profile = replace(self._profile, jitter_ms=milliseconds)
        self._refresh_safety_view()
        self._emit_profile()

    def _load_coordinates(self) -> None:
        if self._profile.target_x is not None:
            self.fixed_x.setText(str(self._profile.target_x))
        if self._profile.target_y is not None:
            self.fixed_y.setText(str(self._profile.target_y))
        self.clear_position_button.setEnabled(
            self._profile.target_x is not None or self._profile.target_y is not None
        )

    def _emit_profile(self) -> None:
        self.profile_changed.emit(self._profile)
