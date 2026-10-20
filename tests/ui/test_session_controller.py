import pytest

from clickforge.core.engine import EngineError
from clickforge.core.models import ClickProfile, RepeatMode, SessionState
from clickforge.ui.session_controller import SessionController


class FakeBackend:
    def __init__(self) -> None:
        self.clicks = 0

    def click(self, *, button, click_type, position=None) -> None:
        self.clicks += 1

    def close(self) -> None:
        pass


def test_controller_emits_state_stats_and_finished(qtbot):
    backend = FakeBackend()
    controller = SessionController(lambda: backend)
    stats: list[tuple[int, float, float]] = []
    states: list[SessionState] = []
    controller.stats_changed.connect(lambda *args: stats.append(args))
    controller.state_changed.connect(lambda state, reason: states.append(state))

    profile = ClickProfile(
        interval_ms=1,
        repeat_mode=RepeatMode.FIXED,
        repeat_count=4,
        session_limit_enabled=False,
    )
    with qtbot.waitSignal(controller.finished, timeout=3000) as blocker:
        controller.start(profile)

    state, reason = blocker.args
    assert state is SessionState.COMPLETED
    assert "4 repeats" in reason
    assert backend.clicks == 4
    assert SessionState.RUNNING in states
    assert SessionState.COMPLETED in states
    assert stats[-1][0] == 4
    assert controller.snapshot().completed_clicks == 4
    controller.close()


def test_controller_rejects_invalid_profiles_without_starting(qtbot):
    controller = SessionController(FakeBackend)
    with pytest.raises(EngineError):
        controller.start(ClickProfile(interval_ms=0))
    assert controller.active is False
    controller.close()
