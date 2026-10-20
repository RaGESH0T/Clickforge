from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QDialog

from clickforge.ui.dialogs.position_picker import PositionPicker, PositionPickerDialog


def _mouse_press(global_x: int, global_y: int) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(40, 60),
        QPointF(global_x, global_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_position_picker_returns_the_clicked_global_point(qtbot):
    picker = PositionPickerDialog()
    qtbot.addWidget(picker)

    picker.mousePressEvent(_mouse_press(640, 480))

    assert picker.result() == QDialog.DialogCode.Accepted
    assert picker.selected_point is not None
    assert (picker.selected_point.x(), picker.selected_point.y()) == (640, 480)


def test_position_picker_can_be_cancelled_with_escape(qtbot):
    picker = PositionPickerDialog()
    qtbot.addWidget(picker)

    picker.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )

    assert picker.result() == QDialog.DialogCode.Rejected
    assert picker.selected_point is None


def test_position_picker_uses_the_live_x11_worker(qtbot, monkeypatch):
    from clickforge.backends import pointer_picker as pointer_module

    class FakeWorker:
        def __init__(self, on_finished, display_name=None) -> None:
            self._on_finished = on_finished

        def start(self) -> bool:
            self._on_finished((120, 240))
            return True

        def cancel(self) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(pointer_module, "X11PointerPicker", FakeWorker)
    picker = PositionPicker(backend="x11")

    with qtbot.waitSignal(picker.point_selected, timeout=1000) as blocker:
        assert picker.start() is True

    assert blocker.args == [(120, 240)]


def test_position_picker_uses_the_live_windows_worker(qtbot, monkeypatch):
    from clickforge.backends import pointer_picker as pointer_module

    class FakeWorker:
        def __init__(self, on_finished, display_name=None) -> None:
            self._on_finished = on_finished

        def start(self) -> bool:
            self._on_finished((320, 480))
            return True

        def cancel(self) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(pointer_module, "WindowsPointerPicker", FakeWorker)
    picker = PositionPicker(backend="windows")

    with qtbot.waitSignal(picker.point_selected, timeout=1000) as blocker:
        assert picker.start() is True

    assert blocker.args == [(320, 480)]
