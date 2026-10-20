from clickforge.core.formatting import (
    format_action,
    format_count,
    format_duration,
    format_interval,
    format_interval_range,
    format_rate,
    format_repeat,
    format_session_limit,
    format_target,
)
from clickforge.core.models import (
    ClickProfile,
    ClickType,
    MouseButton,
    RepeatMode,
    TargetMode,
)


def test_format_interval_uses_compact_units():
    assert format_interval(0) == "0 ms"
    assert format_interval(100) == "100 ms"
    assert format_interval(1000) == "1 s"
    assert format_interval(1500) == "1.5 s"
    assert format_interval(90_000) == "1 min 30 s"
    assert format_interval(3_600_000) == "1 h"
    assert format_interval(5_400_000) == "1 h 30 min"


def test_format_duration_handles_short_and_long_sessions():
    assert format_duration(0) == "00:00.0"
    assert format_duration(65.4) == "01:05.4"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(-4) == "00:00.0"


def test_small_formatting_helpers():
    assert format_rate(9.99) == "10.0"
    assert format_rate(-1) == "0.0"
    assert format_count(None) == "-"
    assert format_count(1234) == "1,234"
    assert format_interval_range(100, 100) == "100 ms"
    assert format_interval_range(100, 150) == "100 ms - 150 ms"


def test_profile_summary_helpers():
    continuous = ClickProfile()
    assert format_target(continuous) == "Follow pointer"
    assert format_repeat(continuous) == "Until stopped"
    assert format_action(continuous) == "Left / Single"
    assert format_session_limit(continuous) == "Auto-stop 30 min"

    fixed = ClickProfile(
        repeat_mode=RepeatMode.FIXED,
        repeat_count=25,
        click_type=ClickType.DOUBLE,
        mouse_button=MouseButton.RIGHT,
        target_mode=TargetMode.FIXED,
        target_x=10,
        target_y=20,
        session_limit_enabled=False,
    )
    assert format_target(fixed) == "Fixed (10, 20)"
    assert format_repeat(fixed) == "25 repeats / 50 clicks"
    assert format_action(fixed) == "Right / Double"
    assert format_session_limit(fixed) == "No auto-stop"

    missing_point = ClickProfile(target_mode=TargetMode.FIXED)
    assert format_target(missing_point) == "No point selected"
