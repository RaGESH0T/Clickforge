"""Coordinate pickers used by the fixed-target control."""

from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QDialog, QWidget

from clickforge.ui import theme

_INSTRUCTION_HEIGHT = 62


class PositionPickerDialog(QDialog):
    """Show a dimmed desktop snapshot and return the point the user clicks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selected_point: QPoint | None = None
        self._cursor: QPoint | None = None
        self._origin = QPoint(0, 0)
        self._shots: list[tuple[QRect, QPixmap]] = []

        self.setWindowTitle("Pick a click position")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._capture_desktop()

    def _capture_desktop(self) -> None:
        screens = QGuiApplication.screens()
        if not screens:
            self.setGeometry(QRect(0, 0, 1, 1))
            return
        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        self._origin = geometry.topLeft()
        self.setGeometry(geometry)
        for screen in screens:
            shot = screen.grabWindow(0)
            self._shots.append((screen.geometry(), shot))

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#080C0A"))
        for geometry, shot in self._shots:
            target = QRect(geometry.topLeft() - self._origin, geometry.size())
            if not shot.isNull():
                painter.drawPixmap(target, shot)
        painter.fillRect(self.rect(), QColor(4, 9, 6, 150))

        if self._cursor is not None:
            pen = QPen(QColor(theme.ACCENT), 1)
            painter.setPen(pen)
            painter.drawLine(0, self._cursor.y(), self.width(), self._cursor.y())
            painter.drawLine(self._cursor.x(), 0, self._cursor.x(), self.height())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self._cursor, 9, 9)

        self._paint_instructions(painter)

    def _paint_instructions(self, painter: QPainter) -> None:
        width = min(430, max(280, self.width() - 40))
        box = QRect((self.width() - width) // 2, 24, width, _INSTRUCTION_HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(12, 20, 15, 235))
        painter.drawRoundedRect(box, 10, 10)
        painter.setBrush(QColor(theme.ACCENT))
        painter.drawRoundedRect(QRect(box.x() + 14, box.y() + 16, 4, 30), 2, 2)

        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(max(9.0, title_font.pointSizeF() + 2))
        painter.setFont(title_font)
        painter.setPen(QColor("#F1F5F2"))
        painter.drawText(
            QRect(box.x() + 30, box.y() + 10, box.width() - 42, 24),
            Qt.AlignmentFlag.AlignVCenter,
            "Click the target location",
        )

        detail_font = QFont(self.font())
        detail_font.setPointSizeF(max(7.0, detail_font.pointSizeF() - 1))
        painter.setFont(detail_font)
        painter.setPen(QColor("#A3B3A9"))
        painter.drawText(
            QRect(box.x() + 30, box.y() + 33, box.width() - 42, 20),
            Qt.AlignmentFlag.AlignVCenter,
            "Esc or right-click cancels",
        )

        if self._cursor is not None:
            global_point = self._cursor + self._origin
            text = f"{global_point.x():,}, {global_point.y():,}"
            painter.setPen(QColor(theme.ACCENT))
            painter.drawText(
                QRect(0, self.height() - 44, self.width(), 24),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._cursor = event.position().toPoint()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self.reject()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_point = event.globalPosition().toPoint()
            self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


class PositionPicker(QObject):
    """Coordinate picker that keeps the desktop live on X11."""

    point_selected = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        backend: str = "x11",
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._backend = backend
        self._worker = None
        self._dialog: PositionPickerDialog | None = None
        self._closed = False

    def start(self) -> bool:
        if self._backend in {"x11", "windows"}:
            from clickforge.backends.pointer_picker import (
                WindowsPointerPicker,
                X11PointerPicker,
            )

            picker_class = X11PointerPicker if self._backend == "x11" else WindowsPointerPicker
            worker = picker_class(self._on_native_result)
            self._worker = worker
            if worker.start():
                return True
            self._worker = None
            return False

        dialog = PositionPickerDialog(self._parent)
        self._dialog = dialog
        dialog.finished.connect(self._on_dialog_finished)
        dialog.open()
        return True

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
        if self._dialog is not None:
            self._dialog.reject()

    def close(self) -> None:
        self._closed = True
        if self._worker is not None:
            self._worker.close()
            self._worker = None
        if self._dialog is not None:
            self._dialog.reject()
            self._dialog.deleteLater()
            self._dialog = None

    def _on_native_result(self, point: tuple[int, int] | None) -> None:
        self._worker = None
        if self._closed:
            return
        self.point_selected.emit(point)

    def _on_dialog_finished(self, _result: int) -> None:
        dialog = self._dialog
        self._dialog = None
        if dialog is None:
            return
        point = dialog.selected_point
        dialog.deleteLater()
        if self._closed:
            return
        if point is None:
            self.point_selected.emit(None)
        else:
            self.point_selected.emit((point.x(), point.y()))
