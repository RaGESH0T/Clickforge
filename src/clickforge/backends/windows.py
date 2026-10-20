"""Windows input backend built on SendInput."""

from __future__ import annotations

import contextlib
import ctypes
import sys
from ctypes import wintypes

from clickforge.backends.base import BackendUnavailable, InputBackendError
from clickforge.core.models import ClickType, MouseButton

_MOUSE_FLAGS = {
    MouseButton.LEFT: (0x0002, 0x0004),
    MouseButton.RIGHT: (0x0008, 0x0010),
    MouseButton.MIDDLE: (0x0020, 0x0040),
}

_ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class WindowsInputBackend:
    """Send synthetic clicks using the Win32 SendInput API."""

    def __init__(self) -> None:
        if sys.platform != "win32":  # pragma: no cover - platform specific
            raise BackendUnavailable("The Windows input backend is only available on Windows.")
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(_INPUT),
            ctypes.c_int,
        )
        self._user32.SendInput.restype = wintypes.UINT
        self._user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._set_dpi_awareness()
        self._closed = False

    def _set_dpi_awareness(self) -> None:
        try:
            self._user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
        except (AttributeError, OSError):
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            with contextlib.suppress(AttributeError, OSError):
                self._user32.SetProcessDPIAware()

    def click(
        self,
        *,
        button: MouseButton,
        click_type: ClickType,
        position: tuple[int, int] | None = None,
    ) -> None:
        if self._closed:
            raise InputBackendError("The Windows input backend is closed.")
        if position is not None and not self._user32.SetCursorPos(
            int(position[0]), int(position[1])
        ):
            error = ctypes.get_last_error()
            raise InputBackendError(
                f"Windows could not move the pointer to the fixed target (error {error})."
            )
        down_flag, up_flag = _MOUSE_FLAGS[button]
        count = 2 if click_type is ClickType.DOUBLE else 1
        events = (_INPUT * (count * 2))()
        for index in range(count):
            events[index * 2].type = 0
            events[index * 2].mi.dwFlags = down_flag
            events[index * 2 + 1].type = 0
            events[index * 2 + 1].mi.dwFlags = up_flag
        sent = self._user32.SendInput(len(events), events, ctypes.sizeof(_INPUT))
        if sent != len(events):
            error = ctypes.get_last_error()
            raise InputBackendError(f"Windows blocked or failed synthetic input (error {error}).")

    def close(self) -> None:
        self._closed = True
