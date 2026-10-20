import time

import pytest

from clickforge.backends.base import InputBackendError
from clickforge.core.engine import ClickEngine, EngineError
from clickforge.core.models import (
    ClickProfile,
    ClickType,
    MouseButton,
    RepeatMode,
    SessionState,
    TargetMode,
)


class FakeBackend:
    def __init__(self) -> None:
        self.clicks: list[tuple[MouseButton, ClickType, tuple[int, int] | None]] = []
        self.closed = False
        self.on_click = None

    def click(
        self,
        *,
        button: MouseButton,
        click_type: ClickType,
        position: tuple[int, int] | None = None,
    ) -> None:
        self.clicks.append((button, click_type, position))
        if self.on_click is not None:
            self.on_click(len(self.clicks))

    def close(self) -> None:
        self.closed = True


def test_fixed_double_click_session_completes_and_reports_counts():
    backend = FakeBackend()
    engine = ClickEngine(lambda: backend)
    profile = ClickProfile(
        interval_ms=1,
        repeat_mode=RepeatMode.FIXED,
        repeat_count=5,
        click_type=ClickType.DOUBLE,
        session_limit_enabled=False,
    )

    engine.start(profile)

    assert engine.wait(2)
    snapshot = engine.snapshot()
    assert snapshot.state is SessionState.COMPLETED
    assert snapshot.completed_repeats == 5
    assert snapshot.completed_clicks == 10
    assert len(backend.clicks) == 5
    assert all(click[1] is ClickType.DOUBLE for click in backend.clicks)


def test_fixed_target_is_forwarded_to_the_backend():
    backend = FakeBackend()
    engine = ClickEngine(lambda: backend)
    profile = ClickProfile(
        interval_ms=1,
        repeat_mode=RepeatMode.FIXED,
        repeat_count=2,
        target_mode=TargetMode.FIXED,
        target_x=-120,
        target_y=440,
        session_limit_enabled=False,
    )

    engine.start(profile)
    assert engine.wait(2)
    assert backend.clicks == [
        (MouseButton.LEFT, ClickType.SINGLE, (-120, 440)),
        (MouseButton.LEFT, ClickType.SINGLE, (-120, 440)),
    ]


def test_stop_is_checked_before_every_repeat():
    backend = FakeBackend()
    engine = ClickEngine(lambda: backend)
    backend.on_click = lambda count: engine.request_stop() if count == 3 else None
    profile = ClickProfile(interval_ms=1)

    engine.start(profile)
    assert engine.wait(2)
    snapshot = engine.snapshot()
    assert snapshot.state is SessionState.IDLE
    assert snapshot.completed_repeats == 3
    assert len(backend.clicks) == 3


def test_pause_halts_clicks_and_resume_continues():
    backend = FakeBackend()
    engine = ClickEngine(lambda: backend)
    backend.on_click = lambda count: engine.request_pause() if count == 1 else None
    profile = ClickProfile(
        interval_ms=5,
        repeat_mode=RepeatMode.FIXED,
        repeat_count=4,
        session_limit_enabled=False,
    )

    engine.start(profile)
    deadline = time.monotonic() + 2
    while engine.state is not SessionState.PAUSED and time.monotonic() < deadline:
        time.sleep(0.005)

    assert engine.state is SessionState.PAUSED
    clicks_while_paused = len(backend.clicks)
    time.sleep(0.05)
    assert len(backend.clicks) == clicks_while_paused

    assert engine.request_resume() is True
    assert engine.wait(2)
    assert engine.snapshot().state is SessionState.COMPLETED
    assert len(backend.clicks) == 4


def test_backend_failure_moves_the_session_to_error():
    class BrokenBackend(FakeBackend):
        def click(self, **kwargs) -> None:
            raise InputBackendError("Input was blocked.")

    backend = BrokenBackend()
    engine = ClickEngine(lambda: backend)
    profile = ClickProfile(interval_ms=1, session_limit_enabled=False)

    engine.start(profile)
    assert engine.wait(2)
    snapshot = engine.snapshot()
    assert snapshot.state is SessionState.ERROR
    assert "blocked" in snapshot.reason


def test_session_limit_finishes_the_session():
    class AdvancingClock:
        def __init__(self) -> None:
            self.now = 0.0

        def __call__(self) -> float:
            self.now += 0.5
            return self.now

    backend = FakeBackend()
    engine = ClickEngine(lambda: backend, clock=AdvancingClock())
    profile = ClickProfile(interval_ms=1, session_limit_minutes=1)

    engine.start(profile)
    assert engine.wait(2)
    snapshot = engine.snapshot()
    assert snapshot.state is SessionState.COMPLETED
    assert "auto-stop" in snapshot.reason
    assert snapshot.completed_repeats > 0


def test_invalid_profiles_never_start_a_thread_or_send_input():
    backend = FakeBackend()
    engine = ClickEngine(lambda: backend)

    with pytest.raises(EngineError, match="at least 1 ms"):
        engine.start(ClickProfile(interval_ms=0))
    with pytest.raises(EngineError, match="X and Y"):
        engine.start(ClickProfile(target_mode=TargetMode.FIXED))
    with pytest.raises(EngineError, match="Repeat count"):
        engine.start(ClickProfile(repeat_mode=RepeatMode.FIXED, repeat_count=0))
    assert backend.clicks == []


def test_jitter_is_bounded_by_the_profile_range():
    class HighRng:
        def uniform(self, low: float, high: float) -> float:
            return high

    profile = ClickProfile(interval_ms=100, jitter_enabled=True, jitter_ms=25)
    engine = ClickEngine(lambda: FakeBackend(), rng=HighRng())  # type: ignore[arg-type]
    assert engine._next_delay_seconds(profile) == pytest.approx(0.125)
