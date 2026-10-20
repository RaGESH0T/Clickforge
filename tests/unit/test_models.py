from dataclasses import FrozenInstanceError

import pytest

from clickforge.core.models import (
    ClickProfile,
    ClickType,
    RepeatMode,
    TargetMode,
)


def test_default_profile_is_safe_and_predictable():
    profile = ClickProfile()
    assert profile.interval_ms == 100
    assert profile.estimated_clicks_per_second == 10.0
    assert profile.total_planned_clicks is None
    assert profile.session_limit_seconds == 1800
    assert profile.timing_range_ms == (100, 100)
    assert profile.has_fixed_target is False


def test_double_click_multiplies_total_but_not_interval():
    profile = ClickProfile(
        repeat_mode=RepeatMode.FIXED,
        repeat_count=250,
        click_type=ClickType.DOUBLE,
    )
    assert profile.clicks_per_repeat == 2
    assert profile.total_planned_clicks == 500
    assert profile.estimated_clicks_per_second == 20.0


def test_jitter_range_is_bounded_and_clamped():
    profile = ClickProfile(interval_ms=10, jitter_enabled=True, jitter_ms=50)
    assert profile.timing_range_ms == (1, 60)

    wide = ClickProfile(interval_ms=100, jitter_enabled=True, jitter_ms=10_000)
    assert wide.timing_range_ms == (1, 10_100)


def test_session_limit_and_fixed_target_state():
    profile = ClickProfile(session_limit_enabled=False)
    assert profile.session_limit_seconds is None

    fixed = ClickProfile(target_mode=TargetMode.FIXED, target_x=5)
    assert fixed.has_fixed_target is True
    assert ClickProfile(target_mode=TargetMode.FIXED).has_fixed_target is False


def test_profiles_are_immutable_and_interval_updates_copy():
    profile = ClickProfile()
    with pytest.raises(FrozenInstanceError):
        profile.interval_ms = 5  # type: ignore[misc]

    changed = profile.with_interval_ms(250)
    assert changed.interval_ms == 250
    assert profile.interval_ms == 100
