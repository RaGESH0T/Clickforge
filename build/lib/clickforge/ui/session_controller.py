"""Qt bridge between the click engine and the interface."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from clickforge.backends.base import InputBackend
from clickforge.core.engine import ClickEngine, EngineEvent, EngineSnapshot, is_terminal_state
from clickforge.core.models import ClickProfile, SessionState


class SessionController(QObject):
    state_changed = Signal(object, str)
    stats_changed = Signal(int, float, float)
    finished = Signal(object, str)
    _engine_event = Signal(object)

    def __init__(
        self,
        backend_factory: Callable[[], InputBackend],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = ClickEngine(backend_factory, listener=self._on_engine_event)
        self._engine_event.connect(self._handle_engine_event)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._emit_stats)

    @property
    def state(self) -> SessionState:
        return self._engine.state

    @property
    def active(self) -> bool:
        return self._engine.active

    def snapshot(self) -> EngineSnapshot:
        return self._engine.snapshot()

    def start(self, profile: ClickProfile) -> None:
        self._engine.start(profile)
        self._emit_stats()
        self._poll_timer.start()

    def request_stop(self) -> bool:
        return self._engine.request_stop()

    def request_pause(self) -> bool:
        return self._engine.request_pause()

    def request_resume(self) -> bool:
        return self._engine.request_resume()

    def close(self) -> None:
        self._poll_timer.stop()
        self._engine.close()

    def _on_engine_event(self, event: EngineEvent) -> None:
        self._engine_event.emit(event)

    def _handle_engine_event(self, event: EngineEvent) -> None:
        self.state_changed.emit(event.state, event.reason)
        if is_terminal_state(event.state):
            self._poll_timer.stop()
            self._emit_stats()
            self.finished.emit(event.state, event.reason)

    def _emit_stats(self) -> None:
        snapshot = self._engine.snapshot()
        self.stats_changed.emit(
            snapshot.completed_clicks,
            snapshot.elapsed_seconds,
            snapshot.measured_rate,
        )
