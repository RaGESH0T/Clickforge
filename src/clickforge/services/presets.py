"""Built-in, editable-in-a-later-milestone click presets."""

from __future__ import annotations

from dataclasses import dataclass

from clickforge.core.formatting import format_interval
from clickforge.core.models import (
    ClickProfile,
    ClickType,
    MouseButton,
    RepeatMode,
)


@dataclass(frozen=True, slots=True)
class Preset:
    key: str
    name: str
    profile: ClickProfile

    @property
    def summary(self) -> str:
        profile = self.profile
        repeat = (
            "Continuous"
            if profile.repeat_mode is RepeatMode.CONTINUOUS
            else (f"{profile.repeat_count:,} repeats")
        )
        button = profile.mouse_button.value.capitalize()
        click = profile.click_type.value.capitalize()
        return f"{format_interval(profile.interval_ms)} · {button} · {click} · {repeat}"


BUILTIN_PRESETS: tuple[Preset, ...] = (
    Preset(
        key="balanced",
        name="Balanced",
        profile=ClickProfile(
            interval_ms=100,
            mouse_button=MouseButton.LEFT,
            click_type=ClickType.SINGLE,
            repeat_mode=RepeatMode.CONTINUOUS,
        ),
    ),
    Preset(
        key="rapid",
        name="Rapid taps",
        profile=ClickProfile(
            interval_ms=50,
            mouse_button=MouseButton.LEFT,
            click_type=ClickType.DOUBLE,
            repeat_mode=RepeatMode.FIXED,
            repeat_count=250,
        ),
    ),
    Preset(
        key="steady",
        name="Slow & steady",
        profile=ClickProfile(
            interval_ms=1000,
            mouse_button=MouseButton.RIGHT,
            click_type=ClickType.SINGLE,
            repeat_mode=RepeatMode.CONTINUOUS,
        ),
    ),
)


def preset_by_key(key: str) -> Preset | None:
    return next((preset for preset in BUILTIN_PRESETS if preset.key == key), None)
