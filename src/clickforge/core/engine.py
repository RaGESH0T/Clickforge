"""Threaded, cancellable click session engine.

The engine deliberately has no Qt dependency. The UI observes it through a
listener callback and a thread-safe snapshot, which keeps the scheduling logic
easy to test with fake backends and clocks.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from clickforge.backends.base import (
    BackendUnavailable,
    InputBackend,
    InputBackendError,
)
from clickforge.core.models import (
    MIN_INTERVAL_MS,
    ClickProfile,
    ClickType,
    RepeatMode,
    SessionState,
    TargetMode,
)
from clickforge.core.validation import validate_profile

LOG = logging.getLogger(__name__)
_TERMINAL_STATES = {SessionState.IDLE, SessionState.COMPLETED, SessionState.ERROR}


class EngineError(RuntimeError):
    """Raised when a session cannot be started or controlled."""


@dataclass(frozen=True, slots=True)
class EngineEvent:
    state: SessionState
    reason: str = ""


@dataclass(frozen=True, slots=True)
class EngineSnapshot:
    state: SessionState
    completed_clicks: int
    completed_repeats: int
    elapsed_seconds: float
    measured_rate: float
    reason: str = ""


class ClickEngine:
    """Run one click session at a time on a background thread."""

    def __init__(
        self,
        backend_factory: Callable[[], InputBackend],
        *,
        listener: Callable[[EngineEvent], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._backend_factory = backend_factory
        self._backend: InputBackend | None = None
        self._listener = listener
        self._clock = clock
        self._rng = rng or random.Random()
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop_requested = threading.Event()
        self._pause_requested = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._state = SessionState.IDLE
        self._profile = ClickProfile()
        self._reason = ""
        self._started_at: float | None = None
        self._finished_at: float | None = None
        self._paused_at: float | None = None
        self._paused_total = 0.0
        self._completed_repeats = 0
        self._completed_clicks = 0

    @property
    def state(self) -> SessionState:
        with self._lock:
            return self._state

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    def set_listener(self, listener: Callable[[EngineEvent], None] | None) -> None:
        self._listener = listener

    def start(self, profile: ClickProfile) -> None:
        """Start a session or raise :class:`EngineError` without sending input."""
        problem = validate_profile(profile)
        if problem:
            raise EngineError(problem)
        with self._lock:
            if self._active:
                raise EngineError("A click session is already running.")
            self._profile = profile
            self._active = True
            self._state = SessionState.RUNNING
            self._reason = ""
            self._started_at = self._clock()
            self._finished_at = None
            self._paused_at = None
            self._paused_total = 0.0
            self._completed_repeats = 0
            self._completed_clicks = 0
            self._stop_requested.clear()
            self._pause_requested.clear()
            self._wake.clear()
            thread = threading.Thread(
                target=self._run,
                args=(profile,),
                name="clickforge-click-engine",
                daemon=True,
            )
            self._thread = thread
            event = EngineEvent(SessionState.RUNNING, "Session started.")
        self._publish(event)
        thread.start()

    def request_pause(self) -> bool:
        with self._lock:
            if not self._active or self._state is not SessionState.RUNNING:
                return False
            self._pause_requested.set()
            self._paused_at = self._clock()
            self._state = SessionState.PAUSED
            self._wake.set()
            self._publish(EngineEvent(SessionState.PAUSED, "Session paused."))
        return True

    def request_resume(self) -> bool:
        with self._lock:
            if not self._active or self._state is not SessionState.PAUSED:
                return False
            self._resume_clock_locked()
            self._pause_requested.clear()
            self._state = SessionState.RUNNING
            self._wake.set()
            self._publish(EngineEvent(SessionState.RUNNING, "Session resumed."))
        return True

    def request_stop(self) -> bool:
        with self._lock:
            if not self._active:
                return False
            self._stop_requested.set()
            self._wake.set()
            self._state = SessionState.STOPPING
            self._publish(EngineEvent(SessionState.STOPPING, "Stopping safely."))
        return True

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for the worker to finish. Returns ``True`` when it is stopped."""
        with self._lock:
            thread = self._thread
        if thread is None or thread is threading.current_thread():
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def stop(self, timeout: float | None = 3.0) -> bool:
        self.request_stop()
        return self.wait(timeout)

    def close(self) -> None:
        if not self.stop():
            LOG.warning("Click engine did not stop before shutdown; leaving backend open")
            return
        with self._lock:
            backend = self._backend
            self._backend = None
        if backend is not None:
            try:
                backend.close()
            except Exception:
                LOG.exception("Could not close the input backend cleanly")

    def snapshot(self) -> EngineSnapshot:
        with self._lock:
            now = self._clock()
            elapsed = self._elapsed_locked(now)
            rate = self._completed_clicks / elapsed if elapsed > 0 else 0.0
            return EngineSnapshot(
                state=self._state,
                completed_clicks=self._completed_clicks,
                completed_repeats=self._completed_repeats,
                elapsed_seconds=elapsed,
                measured_rate=rate,
                reason=self._reason,
            )

    def _run(self, profile: ClickProfile) -> None:
        try:
            backend = self._ensure_backend()
            self._loop(profile, backend)
        except BackendUnavailable as exc:
            LOG.warning("Input backend unavailable: %s", exc)
            self._finish(SessionState.ERROR, str(exc))
        except InputBackendError as exc:
            LOG.warning("Input backend failed: %s", exc)
            self._finish(SessionState.ERROR, str(exc))
        except Exception as exc:
            LOG.exception("Unexpected click engine failure")
            self._finish(
                SessionState.ERROR,
                f"The click session stopped because of an unexpected error: {exc}",
            )

    def _ensure_backend(self) -> InputBackend:
        with self._lock:
            if self._backend is not None:
                return self._backend
        backend = self._backend_factory()
        with self._lock:
            self._backend = backend
            return backend

    def _loop(self, profile: ClickProfile, backend: InputBackend) -> None:
        first_repeat = True
        while True:
            if self._stop_requested.is_set():
                self._finish(SessionState.IDLE, "Session stopped.")
                return
            if self._pause_requested.is_set():
                self._block_while_paused()
                continue
            if self._limits_reached(profile):
                return
            if not first_repeat:
                delay = self._next_delay_seconds(profile)
                remaining = self._remaining_limit_seconds(profile)
                if remaining is not None:
                    delay = min(delay, remaining)
                if self._wait(delay):
                    continue
                if self._stop_requested.is_set() or self._pause_requested.is_set():
                    continue
                if self._limits_reached(profile):
                    return
            position = self._target_position(profile)
            try:
                backend.click(
                    button=profile.mouse_button,
                    click_type=profile.click_type,
                    position=position,
                )
            except InputBackendError:
                raise
            except Exception as exc:
                raise InputBackendError(f"Could not send the click: {exc}") from exc
            with self._lock:
                self._completed_repeats += 1
                self._completed_clicks += 1 if profile.click_type is ClickType.SINGLE else 2
            first_repeat = False

    def _limits_reached(self, profile: ClickProfile) -> bool:
        with self._lock:
            repeats = self._completed_repeats
            now = self._clock()
            elapsed = self._elapsed_locked(now)
        if profile.repeat_mode is RepeatMode.FIXED and repeats >= profile.repeat_count:
            self._finish(
                SessionState.COMPLETED,
                f"Completed {repeats:,} repeats.",
            )
            return True
        limit = profile.session_limit_seconds
        if limit is not None and elapsed >= limit:
            self._finish(
                SessionState.COMPLETED,
                f"Safety auto-stop reached after {profile.session_limit_minutes} minutes.",
            )
            return True
        return False

    def _block_while_paused(self) -> None:
        while self._pause_requested.is_set() and not self._stop_requested.is_set():
            self._wake.clear()
            if not self._pause_requested.is_set() or self._stop_requested.is_set():
                break
            self._wake.wait(0.2)

    def _wait(self, delay_seconds: float) -> bool:
        if self._stop_requested.is_set() or self._pause_requested.is_set():
            return True
        self._wake.clear()
        if self._stop_requested.is_set() or self._pause_requested.is_set():
            return True
        return self._wake.wait(delay_seconds)

    def _next_delay_seconds(self, profile: ClickProfile) -> float:
        if profile.jitter_enabled:
            low_ms, high_ms = profile.timing_range_ms
            delay_ms = self._rng.uniform(low_ms, high_ms)
        else:
            delay_ms = profile.interval_ms
        return max(MIN_INTERVAL_MS, delay_ms) / 1000.0

    def _remaining_limit_seconds(self, profile: ClickProfile) -> float | None:
        limit = profile.session_limit_seconds
        if limit is None:
            return None
        with self._lock:
            elapsed = self._elapsed_locked(self._clock())
        return max(0.0, limit - elapsed)

    def _target_position(self, profile: ClickProfile) -> tuple[int, int] | None:
        if profile.target_mode is not TargetMode.FIXED:
            return None
        if profile.target_x is None or profile.target_y is None:
            raise InputBackendError(
                "The fixed target is missing a coordinate. Choose both X and Y."
            )
        return (profile.target_x, profile.target_y)

    def _finish(self, state: SessionState, reason: str) -> None:
        with self._lock:
            if not self._active:
                return
            now = self._clock()
            self._active = False
            if self._paused_at is not None:
                self._paused_total += max(0.0, now - self._paused_at)
                self._paused_at = None
            self._finished_at = now
            self._state = state
            self._reason = reason
            self._publish(EngineEvent(state, reason))

    def _publish(self, event: EngineEvent) -> None:
        listener = self._listener
        if listener is None:
            return
        try:
            listener(event)
        except Exception:
            LOG.exception("Click engine listener raised an exception")

    def _resume_clock_locked(self) -> None:
        if self._paused_at is not None:
            self._paused_total += max(0.0, self._clock() - self._paused_at)
            self._paused_at = None

    def _elapsed_locked(self, now: float) -> float:
        if self._started_at is None:
            return 0.0
        end = self._finished_at if self._finished_at is not None else now
        paused = self._paused_total
        if self._paused_at is not None:
            paused += max(0.0, end - self._paused_at)
        return max(0.0, end - self._started_at - paused)


def is_terminal_state(state: SessionState) -> bool:
    return state in _TERMINAL_STATES
