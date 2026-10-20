"""Input backend contract shared by platform implementations."""

from __future__ import annotations

from typing import Protocol

from clickforge.core.models import ClickType, MouseButton


class InputBackendError(RuntimeError):
    """Raised when synthetic input cannot be delivered."""


class BackendUnavailable(InputBackendError):
    """Raised when the current session cannot support synthetic input."""


class InputBackend(Protocol):
    def click(
        self,
        *,
        button: MouseButton,
        click_type: ClickType,
        position: tuple[int, int] | None = None,
    ) -> None:
        """Send one click (or a double click) at the current or given position."""

    def close(self) -> None:
        """Release any platform resources held by the backend."""
