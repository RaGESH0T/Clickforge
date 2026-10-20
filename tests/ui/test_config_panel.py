from clickforge.core.models import (
    ClickType,
    RepeatMode,
    TargetMode,
)
from clickforge.ui.widgets.config import ClickConfigPanel


def test_interval_fields_emit_a_consistent_profile(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.milliseconds.spin.setValue(250)

    assert panel.profile().interval_ms == 250
    assert panel.interval_summary.text() == "250 ms"
    assert "4.0 clicks/sec" in panel.rate_summary.text()
    assert panel._preset_buttons[250].property("active") is True
    assert panel._preset_buttons[100].property("active") is False


def test_zero_interval_is_flagged_without_crashing(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.milliseconds.spin.setValue(0)

    assert panel.profile().interval_ms == 0
    assert panel.interval_summary.text() == "Invalid interval"
    assert panel.interval_summary.property("role") == "warning"


def test_double_click_and_fixed_repeat_update_the_summary(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.click_type.set_value(ClickType.DOUBLE)
    panel.repeat_mode.set_value(RepeatMode.FIXED)
    panel.repeat_count.spin.setValue(25)

    profile = panel.profile()
    assert profile.click_type is ClickType.DOUBLE
    assert profile.repeat_mode is RepeatMode.FIXED
    assert profile.total_planned_clicks == 50
    assert "25 repeats" in panel.repeat_count_hint.text()
    assert "50 completed clicks" in panel.repeat_count_hint.text()


def test_fixed_target_coordinates_are_stored_and_cleared(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.target_mode.set_value(TargetMode.FIXED)
    panel.fixed_x.setText("120")
    panel.fixed_y.setText("240")

    assert panel.profile().target_x == 120
    assert panel.profile().target_y == 240
    assert panel.profile().has_fixed_target
    assert "120, 240" in panel.target_status.text()
    assert panel.clear_position_button.isEnabled()

    panel.clear_position_button.click()
    assert panel.profile().target_x is None
    assert panel.profile().target_y is None
    assert panel.target_status.text() == "No fixed point selected"


def test_safety_controls_update_profile_and_warning_copy(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.session_limit_minutes.spin.setValue(45)
    assert panel.profile().session_limit_minutes == 45

    panel.auto_stop_toggle.click()
    assert panel.profile().session_limit_enabled is False
    assert panel.session_limit_minutes.isEnabled() is False

    panel.jitter_toggle.click()
    panel.jitter_ms.spin.setValue(120)
    assert panel.profile().jitter_enabled is True
    assert panel.profile().jitter_ms == 120
    assert panel.timing_range_summary.property("role") == "warning"
    assert "larger than the interval" in panel.timing_range_summary.text()


def test_set_profile_round_trips_all_controls(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)
    source = panel.profile()

    panel.set_profile(source.with_interval_ms(1000))

    assert panel.profile().interval_ms == 1000
    assert panel.hours.value() == 0
    assert panel.seconds.value() == 1
    assert panel.milliseconds.value() == 0


def test_click_type_segments_emit_the_selected_single_or_double(qtbot):
    panel = ClickConfigPanel()
    qtbot.addWidget(panel)

    panel.click_type.button_for(ClickType.DOUBLE).click()
    assert panel.profile().click_type is ClickType.DOUBLE

    panel.click_type.button_for(ClickType.SINGLE).click()
    assert panel.profile().click_type is ClickType.SINGLE
