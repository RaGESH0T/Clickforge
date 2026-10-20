"""Human-friendly formatting helpers for the UI and diagnostics."""

from __future__ import annotations

from clickforge.core.models import ClickProfile, RepeatMode, TargetMode


def _trim_number(value: float, decimals: int = 2) -> str:
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return text or "0"


def format_interval(milliseconds: int) -> str:
    """Return a compact interval label such as ``250 ms`` or ``1 min 30 s``."""
    milliseconds = max(0, int(milliseconds))
    if milliseconds < 1000:
        return f"{milliseconds} ms"
    if milliseconds < 60_000:
        seconds = milliseconds / 1000.0
        return f"{_trim_number(seconds, 3)} s"
    total_seconds = milliseconds // 1000
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        if seconds:
            return f"{minutes} min {seconds} s"
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if minutes:
        return f"{hours} h {minutes} min"
    return f"{hours} h"


def format_duration(seconds: float, *, tenths: bool = True) -> str:
    """Format a duration as ``MM:SS.t`` (or ``H:MM:SS`` for long sessions)."""
    seconds = max(0.0, float(seconds))
    total_tenths = int(round(seconds * 10))
    whole_seconds, _ = divmod(total_tenths, 10)
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    if tenths:
        return f"{minutes:02d}:{secs:02d}.{total_tenths % 10}"
    return f"{minutes:02d}:{secs:02d}"


def format_rate(clicks_per_second: float) -> str:
    return f"{max(0.0, clicks_per_second):.1f}"


def format_count(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{max(0, int(value)):,}"


def format_interval_range(low_ms: int, high_ms: int) -> str:
    if low_ms == high_ms:
        return format_interval(low_ms)
    return f"{format_interval(low_ms)} - {format_interval(high_ms)}"


def format_target(profile: ClickProfile) -> str:
    if profile.target_mode is TargetMode.CURSOR:
        return "Follow pointer"
    if profile.target_x is None or profile.target_y is None:
        return "No point selected"
    return f"Fixed ({profile.target_x:,}, {profile.target_y:,})"


def format_repeat(profile: ClickProfile) -> str:
    if profile.repeat_mode is RepeatMode.CONTINUOUS:
        return "Until stopped"
    repeats = f"{format_count(profile.repeat_count)} repeats"
    if profile.click_type.clicks_per_repeat > 1:
        return f"{repeats} / {format_count(profile.total_planned_clicks)} clicks"
    return repeats


def format_action(profile: ClickProfile) -> str:
    button = profile.mouse_button.value.capitalize()
    return f"{button} / {profile.click_type.value.capitalize()}"


def format_session_limit(profile: ClickProfile) -> str:
    if not profile.session_limit_enabled:
        return "No auto-stop"
    return f"Auto-stop {profile.session_limit_minutes} min"
