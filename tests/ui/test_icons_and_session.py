from clickforge.backends.capabilities import BackendCapabilities
from clickforge.core.models import ClickProfile, SessionState, TargetMode
from clickforge.ui.icons import app_icon, make_icon, make_pixmap
from clickforge.ui.widgets.session import SessionPanel


def test_icons_render_and_are_not_null(qtbot):
    pixmap = make_pixmap("crosshair", "#24d17e", 20, 1.0)
    assert not pixmap.isNull()
    assert pixmap.width() == 20
    assert make_icon("play").isNull() is False
    assert app_icon().isNull() is False


def test_session_panel_handles_backend_states(qtbot):
    panel = SessionPanel()
    qtbot.addWidget(panel)
    unavailable = BackendCapabilities(
        backend_id="none",
        display_name="No display",
        available=False,
        session_type="none",
        reason="No DISPLAY",
    )
    panel.set_capabilities(unavailable)
    assert panel.backend_badge.text() == "INPUT  /  UNAVAILABLE"
    assert panel.backend_badge.toolTip() == "No DISPLAY"


def test_session_panel_buttons_follow_engine_and_state(qtbot):
    panel = SessionPanel()
    qtbot.addWidget(panel)
    assert panel.start_button.isEnabled() is False

    panel.set_engine_available(True)
    assert panel.start_button.isEnabled() is True

    panel.set_state(SessionState.RUNNING)
    assert panel.start_button.isEnabled() is False
    assert panel.stop_button.isEnabled() is True

    panel.set_state(SessionState.IDLE)
    assert panel.start_button.isEnabled() is True
    assert panel.stop_button.isEnabled() is False


def test_session_summary_updates_and_warns_when_backstop_is_off(qtbot):
    panel = SessionPanel()
    qtbot.addWidget(panel)
    profile = ClickProfile(
        target_mode=TargetMode.FIXED,
        target_x=20,
        target_y=30,
        session_limit_enabled=False,
    )

    panel.set_summary(profile)

    assert panel.interval_item.value() == "100 ms"
    assert panel.target_item.value() == "Fixed (20, 30)"
    assert panel.safety_note.property("role") == "warning"
    assert "disabled" in panel.safety_note.text()
