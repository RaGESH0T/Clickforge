from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeySequence

import clickforge.ui.main_window as main_window_module
from clickforge.backends.capabilities import BackendCapabilities
from clickforge.core.models import (
    ClickProfile,
    ClickType,
    RepeatMode,
    SessionState,
    TargetMode,
)
from clickforge.services.first_run import FirstRunStore
from clickforge.services.presets import preset_by_key
from clickforge.ui.main_window import MainWindow
from clickforge.ui.session_controller import SessionController


class FakeBackend:
    def __init__(self) -> None:
        self.clicks = 0

    def click(self, *, button, click_type, position=None) -> None:
        self.clicks += 1

    def close(self) -> None:
        pass


def x11_capabilities() -> BackendCapabilities:
    return BackendCapabilities(
        backend_id="linux-x11-xtest",
        display_name="X11 XTEST (python-xlib)",
        available=True,
        session_type="x11",
        supports_global_hotkeys=True,
        supports_position_capture=True,
    )


def wayland_capabilities() -> BackendCapabilities:
    return BackendCapabilities(
        backend_id="linux-wayland-unavailable",
        display_name="Wayland (not supported)",
        available=False,
        session_type="wayland",
        reason="Use an X11 session for synthetic input.",
    )


def test_main_window_starts_in_a_safe_idle_state(qtbot, tmp_path):
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)

    assert window.state is SessionState.IDLE
    assert window.session_panel.start_button.isEnabled() is True
    assert window.session_panel.stop_button.isEnabled() is False
    assert window.session_panel.backend_badge.text() == "INPUT  /  X11 · XTEST"
    assert window.session_panel.interval_item.value() == "100 ms"
    assert window.session_panel.action_item.value() == "Left / Single"
    assert window.config_panel.pick_position_button.isEnabled() is True


def test_default_layout_does_not_need_a_scrollbar_at_1200x900(qtbot, tmp_path):
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)
    window.resize(1200, 900)
    window.show()
    qtbot.wait(30)

    assert window.scroll.horizontalScrollBar().maximum() == 0
    assert window.scroll.verticalScrollBar().maximum() == 0


def test_wayland_explains_why_position_capture_is_disabled(qtbot, tmp_path):
    window = MainWindow(
        capabilities=wayland_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)

    assert window.session_panel.backend_badge.text() == "INPUT  /  UNAVAILABLE"
    assert window.config_panel.pick_position_button.isEnabled() is False
    assert "X11" in window.config_panel.pick_position_button.toolTip()


def test_welcome_panel_can_be_dismissed_and_remembered(qtbot, tmp_path):
    store = FirstRunStore(tmp_path / "ui-state.json")
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=store,
        show_welcome=True,
    )
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(20)

    assert window.welcome_panel.isVisible()
    window.welcome_panel.dismiss_button.click()

    assert store.welcome_seen() is True
    assert window.welcome_panel.isVisible() is False


def test_applying_a_preset_updates_the_whole_window(qtbot, tmp_path):
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)
    rapid = preset_by_key("rapid")
    assert rapid is not None

    window.presets_panel.buttons["rapid"].click()

    assert window.profile == rapid.profile
    assert window.config_panel.profile() == rapid.profile
    assert window.session_panel.interval_item.value() == "50 ms"
    assert window.session_panel.repeat_item.value() == "250 repeats / 500 clicks"
    assert window.stats_panel.progress_text.text() == "0 / 500 clicks"


def test_starting_a_session_updates_stats_and_releases_the_ui(qtbot, tmp_path):
    backend = FakeBackend()
    controller = SessionController(lambda: backend)
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        session_controller=controller,
        show_welcome=False,
    )
    qtbot.addWidget(window)
    window.config_panel.set_profile(
        ClickProfile(
            interval_ms=1,
            repeat_mode=RepeatMode.FIXED,
            repeat_count=3,
            click_type=ClickType.DOUBLE,
            session_limit_enabled=False,
        )
    )

    with qtbot.waitSignal(controller.finished, timeout=3000) as blocker:
        window.session_panel.start_button.click()

    assert blocker.args[0] is SessionState.COMPLETED
    assert backend.clicks == 3
    assert window.stats_panel.clicks_value.text() == "6"
    assert window.session_panel.start_button.isEnabled() is True
    assert window.config_panel.isEnabled() is True


def test_f7_picks_a_fixed_target_on_screen(qtbot, tmp_path, monkeypatch):
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    qtbot.wait(20)

    class FakePicker(QObject):
        point_selected = Signal(object)

        def __init__(self, parent=None, *, backend="x11") -> None:
            super().__init__(parent)

        def start(self) -> bool:
            self.point_selected.emit((321, 654))
            return True

        def deleteLater(self) -> None:
            pass

    monkeypatch.setattr(main_window_module, "PositionPicker", FakePicker)

    assert window._capture_shortcut.key() == QKeySequence("F7")
    qtbot.keyClick(window, Qt.Key.Key_F7)

    assert window.profile.target_mode is TargetMode.FIXED
    assert (window.profile.target_x, window.profile.target_y) == (321, 654)
    assert window.config_panel.profile().target_x == 321
    assert "321" in window.config_panel.target_status.text()


def test_state_changes_update_header_and_actions(qtbot, tmp_path):
    window = MainWindow(
        capabilities=x11_capabilities(),
        first_run_store=FirstRunStore(tmp_path / "ui-state.json"),
        show_welcome=False,
    )
    qtbot.addWidget(window)

    window.set_session_state(SessionState.RUNNING)
    assert window.header.status.current_state is SessionState.RUNNING
    assert window.session_panel.stop_button.isEnabled() is True
    assert window.stats_panel.state_badge.text() == "LIVE"

    window.set_session_state(SessionState.PAUSED)
    assert window.header.status.current_state is SessionState.PAUSED
    assert window.session_panel.stop_button.isEnabled() is True

    window.set_session_state(SessionState.COMPLETED)
    assert window.session_panel.stop_button.isEnabled() is False
    assert window.session_panel.start_button.isEnabled() is True
