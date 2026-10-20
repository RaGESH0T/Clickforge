"""Profile validation shared by the UI and the click engine."""

from __future__ import annotations

from clickforge.core.models import (
    MAX_REPEATS,
    MAX_SESSION_LIMIT_MINUTES,
    MIN_INTERVAL_MS,
    MIN_REPEATS,
    MIN_SESSION_LIMIT_MINUTES,
    ClickProfile,
    RepeatMode,
    TargetMode,
)


def validate_profile(profile: ClickProfile) -> str | None:
    """Return a user-facing problem description, or ``None`` when runnable."""
    if profile.interval_ms < MIN_INTERVAL_MS:
        return "Choose an interval of at least 1 ms before starting."
    if profile.repeat_mode is RepeatMode.FIXED and not (
        MIN_REPEATS <= profile.repeat_count <= MAX_REPEATS
    ):
        return f"Repeat count must be between {MIN_REPEATS} and {MAX_REPEATS:,}."
    if profile.session_limit_enabled and not (
        MIN_SESSION_LIMIT_MINUTES <= profile.session_limit_minutes <= MAX_SESSION_LIMIT_MINUTES
    ):
        return "Auto-stop minutes are outside the supported range."
    if profile.jitter_enabled and profile.jitter_ms < 0:
        return "Random timing variation cannot be negative."
    if profile.target_mode is TargetMode.FIXED and (
        profile.target_x is None or profile.target_y is None
    ):
        return "Choose both an X and Y coordinate for the fixed target."
    return None
