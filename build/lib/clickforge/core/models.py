"""Core data models shared by the UI, scheduler and input backends.

This module deliberately has no Qt or platform imports so it can be tested
quickly and reused by the background worker.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ClickType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"

    @property
    def clicks_per_repeat(self) -> int:
        return 1 if self is ClickType.SINGLE else 2


class RepeatMode(str, Enum):
    CONTINUOUS = "continuous"
    FIXED = "fixed"


class TargetMode(str, Enum):
    CURSOR = "cursor"
    FIXED = "fixed"


class SessionState(str, Enum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


MIN_INTERVAL_MS = 1
MAX_INTERVAL_MS = 24 * 60 * 60 * 1000 - 1
MIN_REPEATS = 1
MAX_REPEATS = 1_000_000
MIN_SESSION_LIMIT_MINUTES = 1
MAX_SESSION_LIMIT_MINUTES = 24 * 60
MAX_JITTER_MS = 60_000


@dataclass(frozen=True, slots=True)
class ClickProfile:
    """The complete, serialisable click configuration.

    ``repeat_count`` always means repeats, not individual click events. A
    double-click repeat sends two click events, which is why the UI shows both
    repeats and total clicks.
    """

    interval_ms: int = 100
    mouse_button: MouseButton = MouseButton.LEFT
    click_type: ClickType = ClickType.SINGLE
    repeat_mode: RepeatMode = RepeatMode.CONTINUOUS
    repeat_count: int = 100
    target_mode: TargetMode = TargetMode.CURSOR
    target_x: int | None = None
    target_y: int | None = None
    session_limit_minutes: int = 30
    session_limit_enabled: bool = True
    jitter_enabled: bool = False
    jitter_ms: int = 10

    @property
    def interval_seconds(self) -> float:
        return self.interval_ms / 1000.0

    @property
    def clicks_per_repeat(self) -> int:
        return self.click_type.clicks_per_repeat

    @property
    def estimated_clicks_per_second(self) -> float:
        if self.interval_ms <= 0:
            return 0.0
        return (1000.0 / self.interval_ms) * self.clicks_per_repeat

    @property
    def total_planned_clicks(self) -> int | None:
        if self.repeat_mode is RepeatMode.CONTINUOUS:
            return None
        return self.repeat_count * self.clicks_per_repeat

    @property
    def session_limit_seconds(self) -> int | None:
        if not self.session_limit_enabled:
            return None
        return self.session_limit_minutes * 60

    @property
    def timing_range_ms(self) -> tuple[int, int]:
        if not self.jitter_enabled:
            return (self.interval_ms, self.interval_ms)
        low = max(MIN_INTERVAL_MS, self.interval_ms - self.jitter_ms)
        high = min(MAX_INTERVAL_MS, self.interval_ms + self.jitter_ms)
        return (low, high)

    @property
    def has_fixed_target(self) -> bool:
        return self.target_mode is TargetMode.FIXED and self.target_x is not None

    def with_interval_ms(self, interval_ms: int) -> ClickProfile:
        return replace(self, interval_ms=interval_ms)


DEFAULT_PROFILE = ClickProfile()
