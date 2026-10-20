"""Global emergency-stop listeners.

The emergency shortcut is only intercepted while a session is active. This
keeps Escape usable in every other application when ClickForge is idle.
"""

from __future__ import annotations

import contextlib
import logging
import select
import sys
import threading
import time
from collections.abc import Callable

from clickforge.backends.capabilities import BackendCapabilities

LOG = logging.getLogger(__name__)


class X11EmergencyStopListener:
    """Grab Escape through X11 while a session is running."""

    def __init__(self, on_stop: Callable[[], None]) -> None:
        self._on_stop = on_stop
        self._armed = threading.Event()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._ready_result = False
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._thread is not None:
            return self._ready_result
        self._thread = threading.Thread(
            target=self._run,
            name="clickforge-global-hotkeys",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(2.0)
        return self._ready_result

    def set_armed(self, armed: bool) -> None:
        if armed:
            self._armed.set()
        else:
            self._armed.clear()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(2.0)

    def _run(self) -> None:
        try:
            from Xlib import XK, X, display

            connection = display.Display()
        except Exception as exc:
            LOG.warning("Global emergency stop is unavailable: %s", exc)
            self._ready.set()
            return
        try:
            root = connection.screen().root
            keycode = connection.keysym_to_keycode(XK.XK_Escape)
            if not keycode:
                LOG.warning("Could not resolve the Escape keycode for global hotkeys")
                return
            masks = (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask)
            errors: list[object] = []
            connection.set_error_handler(lambda error, request: errors.append(error))
            grabbed = False
            retry_at = 0.0
            self._ready_result = True
            self._ready.set()
            while not self._stop.is_set():
                want_grab = self._armed.is_set()
                if want_grab and not grabbed and time.monotonic() >= retry_at:
                    errors.clear()
                    for mask in masks:
                        root.grab_key(
                            keycode,
                            mask,
                            False,
                            X.GrabModeAsync,
                            X.GrabModeAsync,
                        )
                    connection.sync()
                    if errors:
                        LOG.warning("Could not grab Escape globally; will retry")
                        for mask in masks:
                            with contextlib.suppress(Exception):
                                root.ungrab_key(keycode, mask)
                        connection.sync()
                        retry_at = time.monotonic() + 0.5
                    else:
                        grabbed = True
                elif not want_grab and grabbed:
                    for mask in masks:
                        with contextlib.suppress(Exception):
                            root.ungrab_key(keycode, mask)
                    connection.sync()
                    grabbed = False
                if select.select([connection.fileno()], [], [], 0.1)[0]:
                    while connection.pending_events():
                        event = connection.next_event()
                        if event.type == X.KeyPress and self._armed.is_set():
                            self._on_stop()
            if grabbed:
                for mask in masks:
                    with contextlib.suppress(Exception):
                        root.ungrab_key(keycode, mask)
                connection.sync()
        except Exception:
            LOG.exception("Global emergency-stop listener failed")
        finally:
            with contextlib.suppress(Exception):
                connection.close()
            self._ready.set()


class WindowsEmergencyStopListener:
    """Register Escape as a global hotkey through RegisterHotKey."""

    _WM_APP_ARM = 0x8001
    _WM_APP_QUIT = 0x8002
    _HOTKEY_ID = 0xB001

    def __init__(self, on_stop: Callable[[], None]) -> None:
        self._on_stop = on_stop
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._ready_result = False
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._post = None

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._thread is not None:
            return self._ready_result
        self._thread = threading.Thread(
            target=self._run,
            name="clickforge-global-hotkeys",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(2.0)
        return self._ready_result

    def set_armed(self, armed: bool) -> None:
        thread_id = self._thread_id
        if thread_id is None or self._post is None:
            return
        with contextlib.suppress(Exception):
            self._post(thread_id, self._WM_APP_ARM, int(armed), 0)

    def close(self) -> None:
        self._stop.set()
        thread_id = self._thread_id
        if thread_id is not None and self._post is not None:
            with contextlib.suppress(Exception):
                self._post(thread_id, self._WM_APP_QUIT, 0, 0)
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(2.0)

    def _run(self) -> None:
        if sys.platform != "win32":  # pragma: no cover - platform specific
            self._ready.set()
            return
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.GetMessageW.argtypes = (
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        )
        self._post = user32.PostThreadMessageW
        self._thread_id = kernel32.GetCurrentThreadId()
        self._ready_result = True
        self._ready.set()
        armed = False
        try:
            message = wintypes.MSG()
            while not self._stop.is_set():
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result <= 0:
                    break
                if message.message == self._WM_APP_ARM:
                    want = bool(message.wParam)
                    if want and not armed:
                        armed = bool(
                            user32.RegisterHotKey(
                                None,
                                self._HOTKEY_ID,
                                0x4000,
                                0x1B,
                            )
                        )
                        if not armed:
                            LOG.warning("Windows could not register the global Escape hotkey")
                    elif not want and armed:
                        user32.UnregisterHotKey(None, self._HOTKEY_ID)
                        armed = False
                elif message.message == 0x0312 and message.wParam == self._HOTKEY_ID:
                    self._on_stop()
                elif message.message == self._WM_APP_QUIT:
                    break
        except Exception:
            LOG.exception("Windows global emergency-stop listener failed")
        finally:
            if armed:
                with contextlib.suppress(Exception):
                    user32.UnregisterHotKey(None, self._HOTKEY_ID)
            self._thread_id = None


class UnavailableHotkeyListener:
    def start(self) -> bool:
        return False

    def set_armed(self, armed: bool) -> None:
        pass

    def close(self) -> None:
        pass


def create_emergency_stop_listener(
    capabilities: BackendCapabilities,
    on_stop: Callable[[], None],
) -> X11EmergencyStopListener | WindowsEmergencyStopListener | UnavailableHotkeyListener:
    if capabilities.session_type == "x11":
        return X11EmergencyStopListener(on_stop)
    if capabilities.session_type == "windows":
        return WindowsEmergencyStopListener(on_stop)
    return UnavailableHotkeyListener()
