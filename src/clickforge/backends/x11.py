"""X11 input backend built on the XTEST extension."""

from __future__ import annotations

import contextlib
import time

from clickforge.backends.base import BackendUnavailable, InputBackendError
from clickforge.core.models import ClickType, MouseButton

_BUTTONS = {
    MouseButton.LEFT: 1,
    MouseButton.MIDDLE: 2,
    MouseButton.RIGHT: 3,
}
_DOUBLE_CLICK_GAP_SECONDS = 0.01


class X11InputBackend:
    """Send synthetic pointer events through XTEST."""

    def __init__(self, display_name: str | None = None) -> None:
        try:
            from Xlib import X, display
            from Xlib.ext import xtest
        except ImportError as exc:  # pragma: no cover - dependency is platform specific
            raise BackendUnavailable(
                "python-xlib is not installed. Reinstall the application to enable clicking."
            ) from exc

        self._x = X
        try:
            self._display = display.Display(display_name)
        except Exception as exc:
            raise BackendUnavailable(
                "Could not connect to the X11 display. Is DISPLAY set correctly?"
            ) from exc
        try:
            extension = self._display.query_extension("XTEST")
            if extension is None or not extension.present:
                raise BackendUnavailable("This X server does not provide the XTEST extension.")
            self._xtest = xtest
            self._closed = False
        except Exception:
            with contextlib.suppress(Exception):
                self._display.close()
            raise

    def click(
        self,
        *,
        button: MouseButton,
        click_type: ClickType,
        position: tuple[int, int] | None = None,
    ) -> None:
        if self._closed:
            raise InputBackendError("The X11 input backend is closed.")
        button_code = _BUTTONS[button]
        try:
            if position is not None:
                self._xtest.fake_input(
                    self._display,
                    self._x.MotionNotify,
                    x=int(position[0]),
                    y=int(position[1]),
                )
            self._send_click(button_code)
            if click_type is ClickType.DOUBLE:
                self._display.sync()
                time.sleep(_DOUBLE_CLICK_GAP_SECONDS)
                self._send_click(button_code)
            self._display.sync()
        except Exception as exc:
            raise InputBackendError(f"X11 could not send the click: {exc}") from exc

    def _send_click(self, button_code: int) -> None:
        self._xtest.fake_input(self._display, self._x.ButtonPress, button_code)
        self._xtest.fake_input(self._display, self._x.ButtonRelease, button_code)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(Exception):
            self._display.sync()
        with contextlib.suppress(Exception):
            self._display.close()
