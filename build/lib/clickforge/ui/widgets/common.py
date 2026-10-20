"""Small reusable widgets that give the app its visual language."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QFontMetrics,
    QIntValidator,
    QKeyEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from clickforge.core.models import SessionState
from clickforge.ui import theme
from clickforge.ui.icons import make_icon, make_pixmap


def divider(vertical: bool = False) -> QFrame:
    line = QFrame()
    line.setObjectName("DividerV" if vertical else "DividerH")
    if vertical:
        line.setFixedWidth(1)
    else:
        line.setFixedHeight(1)
    return line


def icon_label(name: str, color: str = theme.MUTED, size: int = 16) -> QLabel:
    label = QLabel()
    label.setPixmap(make_pixmap(name, color, size))
    label.setFixedSize(size, size)
    label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    return label


def set_role(widget: QWidget, role: str) -> None:
    widget.setProperty("role", role)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class Panel(QFrame):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margins: tuple[int, int, int, int] = (24, 22, 24, 22),
        spacing: int = 16,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout


class SectionTitle(QWidget):
    def __init__(
        self,
        icon: str,
        title: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(icon_label(icon, theme.MUTED, 15))
        title_label = QLabel(title.upper())
        title_label.setProperty("role", "sectionTitle")
        layout.addWidget(title_label)
        layout.addStretch(1)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setProperty("role", "faint")
            layout.addWidget(hint_label)


class IconButton(QToolButton):
    def __init__(
        self,
        icon_name: str,
        tooltip: str,
        parent: QWidget | None = None,
        *,
        size: int = 36,
        icon_size: int = 18,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setIcon(make_icon(icon_name, theme.MUTED, icon_size, theme.FAINT))
        self.setIconSize(QSize(icon_size, icon_size))
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class Badge(QLabel):
    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        accent: bool = False,
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "badgeAccent" if accent else "badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class KeyCap(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "keycap")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(theme.mono_font(10, QFont.Weight.DemiBold))


class PulseDot(QWidget):
    """A cheap 40 ms pulse that runs only while a session is active."""

    def __init__(self, parent: QWidget | None = None, *, size: int = 16) -> None:
        super().__init__(parent)
        self._size = size
        self._active = False
        self._phase = 0.0
        self._color = QColor(theme.MUTED)
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if active and not self._timer.isActive():
            self._phase = 0.0
            self._timer.start()
        elif not active:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.045) % 1.0
        self.update()

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center = self.rect().center()
        radius = max(2.0, self._size / 2 - 4)
        if self._active:
            ring = QColor(self._color)
            ring.setAlphaF(max(0.0, 0.34 * (1.0 - self._phase)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ring)
            expanding = radius + self._phase * 3.0
            painter.drawEllipse(
                QRectF(center.x() - expanding, center.y() - expanding, expanding * 2, expanding * 2)
            )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(
            QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        )
        painter.end()


_STATE_META: dict[SessionState, tuple[str, str, str]] = {
    SessionState.IDLE: ("Idle", "idle", theme.MUTED),
    SessionState.READY: ("Ready", "accent", theme.ACCENT),
    SessionState.RUNNING: ("Running", "accent", theme.ACCENT),
    SessionState.PAUSED: ("Paused", "warning", theme.WARNING),
    SessionState.STOPPING: ("Stopping", "warning", theme.WARNING),
    SessionState.COMPLETED: ("Completed", "accent", theme.ACCENT),
    SessionState.ERROR: ("Error", "danger", theme.DANGER),
}


class StatusPill(QFrame):
    def __init__(
        self, state: SessionState = SessionState.IDLE, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self._state = state
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 12, 4)
        layout.setSpacing(7)
        self._dot = PulseDot(self, size=14)
        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self._label = QLabel()
        self._label.setObjectName("StatusText")
        self._label.setFont(theme.ui_font(9, QFont.Weight.DemiBold))
        layout.addWidget(self._label)
        self.set_size()
        self.set_state(state)

    def set_size(self) -> None:
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    @property
    def current_state(self) -> SessionState:
        return self._state

    def set_state(self, state: SessionState, text: str | None = None) -> None:
        self._state = state
        label, tone, color = _STATE_META[state]
        self._label.setText(text or label)
        self.setProperty("tone", tone)
        self._dot.set_color(color)
        self._dot.set_active(state in {SessionState.RUNNING, SessionState.STOPPING})
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._position = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(130)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._animate)

    def _on_anim(self, value: object) -> None:
        self._position = float(value)
        self.update()

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        self._anim.stop()
        self._position = 1.0 if checked else 0.0
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (
            Qt.Key.Key_Space,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        enabled = self.isEnabled()
        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if not enabled:
            track_color = QColor("#151E27")
            knob_color = QColor(theme.FAINT)
        elif self.isChecked():
            track_color = QColor(theme.ACCENT)
            knob_color = QColor(theme.ACCENT_TEXT)
        else:
            track_color = QColor("#22303D")
            knob_color = QColor(theme.TEXT_SECONDARY)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, 11, 11)
        knob_x = 3.0 + self._position * 18.0
        painter.setBrush(knob_color)
        painter.drawEllipse(QRectF(knob_x, 3.0, 16.0, 16.0))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(theme.ACCENT_STRONG), 1.2))
            painter.drawRoundedRect(track.adjusted(-1, -1, 1, 1), 12, 12)
        painter.end()


class SegmentedControl(QFrame):
    value_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Segmented")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[Any, QRadioButton] = {}
        self._values: dict[int, Any] = {}
        self._setting = False
        self._next_id = 0
        self._group.buttonToggled.connect(self._on_toggled)

    def add_segment(
        self,
        value: Any,
        text: str,
        *,
        tooltip: str = "",
        accessible_name: str = "",
    ) -> QRadioButton:
        button = QRadioButton(text)
        button.setProperty("segment", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setMinimumHeight(30)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if tooltip:
            button.setToolTip(tooltip)
        button.setAccessibleName(accessible_name or text)
        button_id = self._next_id
        self._next_id += 1
        self._group.addButton(button, button_id)
        self._buttons[value] = button
        self._values[button_id] = value
        self._layout.addWidget(button, 1)
        if len(self._buttons) == 1:
            button.setChecked(True)
        return button

    def _on_toggled(self, button: QAbstractButton, checked: bool) -> None:
        if not checked or self._setting:
            return
        button_id = self._group.id(button)
        value = self._values.get(button_id)
        self.value_changed.emit(value)

    def value(self) -> Any:
        button = self._group.checkedButton()
        if button is None:
            return None
        return self._values.get(self._group.id(button))

    def set_value(self, value: Any) -> None:
        button = self._buttons.get(value)
        if button is None or button.isChecked():
            return
        self._setting = True
        try:
            button.setChecked(True)
        finally:
            self._setting = False
        self.value_changed.emit(value)

    def set_segment_enabled(self, value: Any, enabled: bool) -> None:
        button = self._buttons.get(value)
        if button is not None:
            button.setEnabled(enabled)

    def button_for(self, value: Any) -> QRadioButton | None:
        return self._buttons.get(value)


class NumericField(QLineEdit):
    value_changed = Signal(int)

    def __init__(
        self,
        *,
        minimum: int = 0,
        maximum: int = 999,
        value: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._minimum = minimum
        self._maximum = maximum
        self._value = value
        self._validator = QIntValidator(minimum, maximum, self)
        self.setValidator(self._validator)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setText(str(value))
        self.textEdited.connect(self._on_text_edited)
        self.editingFinished.connect(self._commit_text)

    def setRange(self, minimum: int, maximum: int) -> None:  # noqa: N802
        self._minimum = minimum
        self._maximum = maximum
        self.setValidator(QIntValidator(minimum, maximum, self))
        self.setValue(self._value)

    def minimum(self) -> int:
        return self._minimum

    def maximum(self) -> int:
        return self._maximum

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:  # noqa: N802
        value = max(self._minimum, min(self._maximum, int(value)))
        changed = value != self._value
        self._value = value
        self.setText(str(value))
        self.setCursorPosition(len(self.text()))
        if changed:
            self.value_changed.emit(value)

    def stepBy(self, steps: int) -> None:  # noqa: N802
        self.setValue(self._value + steps)

    def _on_text_edited(self, text: str) -> None:
        if not text:
            return
        try:
            value = int(text)
        except ValueError:
            return
        if value < self._minimum or value > self._maximum:
            return
        if value != self._value:
            self._value = value
            self.value_changed.emit(value)

    def _commit_text(self) -> None:
        if not self.text() or self.text() in {"-", "+"}:
            self.setValue(self._minimum)
            return
        try:
            value = int(self.text())
        except ValueError:
            self.setValue(self._value)
            return
        self.setValue(value)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Up:
            self.stepBy(1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Down:
            self.stepBy(-1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_PageUp:
            self.stepBy(10)
            event.accept()
            return
        if event.key() == Qt.Key.Key_PageDown:
            self.stepBy(-10)
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if not self.hasFocus():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta:
            self.stepBy(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class NumberField(QWidget):
    value_changed = Signal(int)

    def __init__(
        self,
        label: str,
        *,
        minimum: int = 0,
        maximum: int = 999,
        value: int = 0,
        parent: QWidget | None = None,
        accessible_name: str = "",
        width: int | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label_widget = QLabel(label.upper())
        label_widget.setProperty("role", "fieldLabel")
        layout.addWidget(label_widget)
        self.spin = NumericField(minimum=minimum, maximum=maximum, value=value)
        self.spin.setFixedHeight(34)
        self.spin.setFont(theme.mono_font(12, QFont.Weight.Medium))
        self.spin.setAccessibleName(accessible_name or label)
        self.spin.setToolTip(accessible_name or label)
        if width:
            self.spin.setFixedWidth(width)
        layout.addWidget(self.spin)
        self.spin.value_changed.connect(self.value_changed)

    def value(self) -> int:
        return self.spin.value()

    def set_value(self, value: int) -> None:
        self.spin.setValue(value)

    def set_suffix(self, suffix: str) -> None:
        self.spin.setPlaceholderText(suffix)


class SummaryItem(QWidget):
    def __init__(
        self,
        label: str,
        value: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self._label = QLabel(label.upper())
        self._label.setProperty("role", "fieldLabel")
        self._value = QLabel(value)
        self._value.setProperty("role", "summaryStrong")
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def value(self) -> str:
        return self._value.text()

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class StatMetric(QWidget):
    def __init__(
        self,
        label: str,
        value: str = "0",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        label_widget = QLabel(label.upper())
        label_widget.setProperty("role", "fieldLabel")
        self._value = QLabel(value)
        self._value.setProperty("role", "statValue")
        self._value.setFont(theme.mono_font(17, QFont.Weight.DemiBold))
        layout.addWidget(label_widget)
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class PresetButton(QAbstractButton):
    def __init__(
        self,
        title: str,
        summary: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._summary = summary
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(f"Apply {title} preset: {summary}")
        self.setToolTip(f"Apply {title}: {summary}")

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(280, 50)

    def enterEvent(self, event: QEvent) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        if self._hover:
            painter.setBrush(QColor(theme.PANEL_HOVER))
            painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        else:
            painter.setBrush(QColor(theme.PANEL_ALT))
            painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawRoundedRect(rect, 8, 8)

        title_font = QFont(theme.ui_font_family())
        title_font.setPixelSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        summary_font = QFont(theme.ui_font_family())
        summary_font.setPixelSize(10)

        painter.setFont(title_font)
        painter.setPen(QColor(theme.TEXT))
        metrics = QFontMetrics(title_font)
        title = metrics.elidedText(
            self._title,
            Qt.TextElideMode.ElideRight,
            max(20, self.width() - 50),
        )
        painter.drawText(
            QRectF(11, 5, self.width() - 42, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
        painter.setFont(summary_font)
        painter.setPen(QColor(theme.MUTED))
        summary_metrics = QFontMetrics(summary_font)
        summary = summary_metrics.elidedText(
            self._summary,
            Qt.TextElideMode.ElideRight,
            max(20, self.width() - 44),
        )
        painter.drawText(
            QRectF(11, 23, self.width() - 42, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            summary,
        )
        arrow = make_pixmap("arrow-up-right", theme.FAINT, 14)
        painter.drawPixmap(self.width() - 28, (self.height() - 14) // 2, arrow)

        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(theme.ACCENT_STRONG), 1.2))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        painter.end()


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 15, 9)
        layout.setSpacing(9)
        self._icon = icon_label("check", theme.ACCENT, 15)
        self._label = QLabel()
        self._label.setProperty("role", "summaryStrong")
        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(150)
        self._animation.valueChanged.connect(self._set_opacity)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def _set_opacity(self, value: object) -> None:
        self._effect.setOpacity(float(value))

    def show_message(
        self,
        text: str,
        *,
        icon: str = "check",
        tone: str = "accent",
        duration_ms: int = 2600,
    ) -> None:
        color = {
            "accent": theme.ACCENT,
            "warning": theme.WARNING,
            "danger": theme.DANGER,
        }.get(tone, theme.ACCENT)
        self._label.setText(text)
        self._icon.setPixmap(make_pixmap(icon, color, 15))
        self.adjustSize()
        self._position()
        self.show()
        self.raise_()
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._timer.start(duration_ms)

    def _fade_out(self) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.start()
        QTimer.singleShot(170, self.hide)

    def _position(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = max(12, (parent.width() - self.width()) // 2)
        y = max(12, parent.height() - self.height() - 68)
        self.move(QPoint(x, y))

    def reposition(self) -> None:
        if self.isVisible():
            self._position()
