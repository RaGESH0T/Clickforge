"""Live, non-freezing screen position capture for X11."""

from __future__ import annotations

import contextlib
import logging
import select
import threading
from collections.abc import Callable

LOG = logging.getLogger(__name__)


class X11PointerPicker:
    """Grab the pointer until the user clicks, without covering the screen.

    The desktop keeps running normally while the grab is active. Left-click
    reports the root-window coordinates; right-click or Escape cancels.
    """

    def __init__(
        self,
        on_finished: Callable[[tuple[int, int] | None], None],
        display_name: str | None = None,
    ) -> None:
        self._on_finished = on_finished
        self._display_name = display_name
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._ready_result = False
        self._thread: threading.Thread | None = None
        self._connection = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        if self._thread is not None:
            return self._ready_result
        self._thread = threading.Thread(
            target=self._run,
            name="clickforge-pointer-picker",
            daemon=True,
        )
        self._thread.start()
        ready = self._ready.wait(2.0)
        if not ready:
            self._stop.set()
        return self._ready_result and ready

    def cancel(self) -> None:
        self._stop.set()

    def close(self) -> None:
        self.cancel()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(2.0)

    def _run(self) -> None:
        try:
            from Xlib import XK, X, Xcursorfont, display

            connection = display.Display(self._display_name)
        except Exception as exc:
            LOG.warning("Could not start the live position picker: %s", exc)
            self._ready.set()
            return

        with self._lock:
            self._connection = connection
        selected: tuple[int, int] | None = None
        cursor = None
        font = None
        keycode = None
        grabbed_keys: tuple[int, ...] = ()
        try:
            root = connection.screen().root
            try:
                font = connection.open_font("cursor")
                cursor = font.create_glyph_cursor(
                    font,
                    Xcursorfont.crosshair,
                    Xcursorfont.crosshair + 1,
                    (0xFFFF, 0xFFFF, 0xFFFF),
                    (0, 0, 0),
                )
            except Exception:
                LOG.debug("Could not create the crosshair cursor", exc_info=True)
            keycode = connection.keysym_to_keycode(XK.XK_Escape) or None
            if self._stop.is_set():
                return
            status = root.grab_pointer(
                False,
                X.ButtonPressMask | X.ButtonReleaseMask,
                X.GrabModeAsync,
                X.GrabModeAsync,
                X.NONE,
                cursor or X.NONE,
                X.CurrentTime,
            )
            connection.sync()
            if status != X.GrabSuccess:
                LOG.warning("Could not grab the pointer for position capture (status %s)", status)
                return
            if keycode:
                masks = (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask)
                for mask in masks:
                    root.grab_key(
                        keycode,
                        mask,
                        False,
                        X.GrabModeAsync,
                        X.GrabModeAsync,
                    )
                connection.sync()
                grabbed_keys = masks
            self._ready_result = True
            self._ready.set()

            cancelled = False
            while not self._stop.is_set():
                if not select.select([connection.fileno()], [], [], 0.1)[0]:
                    continue
                while connection.pending_events():
                    event = connection.next_event()
                    if event.type == X.ButtonPress:
                        if event.detail == 1:
                            selected = (event.root_x, event.root_y)
                            self._stop.set()
                            break
                        if event.detail == 3:
                            cancelled = True
                            self._stop.set()
                            break
                    elif event.type == X.KeyPress and keycode and event.detail == keycode:
                        cancelled = True
                        self._stop.set()
                        break
                if self._stop.is_set():
                    break
            if cancelled:
                selected = None
        except Exception:
            LOG.exception("Live position picker failed")
            selected = None
        finally:
            with contextlib.suppress(Exception):
                if keycode:
                    for mask in grabbed_keys:
                        root.ungrab_key(keycode, mask)
            with contextlib.suppress(Exception):
                connection.ungrab_pointer(X.CurrentTime)
            with contextlib.suppress(Exception):
                connection.sync()
            if cursor is not None:
                with contextlib.suppress(Exception):
                    cursor.free()
            if font is not None:
                with contextlib.suppress(Exception):
                    font.close()
            with contextlib.suppress(Exception):
                connection.close()
            with self._lock:
                self._connection = None
            self._ready.set()
            if self._ready_result:
                try:
                    self._on_finished(selected)
                except Exception:
                    LOG.exception("Position picker callback failed")


class WindowsPointerPicker:
    """Capture the next click through low-level Windows hooks.

    The desktop remains live because no overlay or screenshot is shown. The
    hook swallows the captured left click; right-click or Escape cancels.
    """

    _WH_KEYBOARD_LL = 13
    _WH_MOUSE_LL = 14
    _WM_QUIT = 0x0012
    _WM_KEYDOWN = 0x0100
    _WM_LBUTTONDOWN = 0x0201
    _WM_RBUTTONDOWN = 0x0204
    _VK_ESCAPE = 0x1B
    _HC_ACTION = 0

    def __init__(self, on_finished: Callable[[tuple[int, int] | None], None]) -> None:
        self._on_finished = on_finished
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._ready_result = False
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._post_message = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        if self._thread is not None:
            return self._ready_result
        self._thread = threading.Thread(
            target=self._run,
            name="clickforge-pointer-picker",
            daemon=True,
        )
        self._thread.start()
        ready = self._ready.wait(2.0)
        if not ready:
            self.cancel()
        return self._ready_result and ready

    def cancel(self) -> None:
        self._stop.set()
        with self._lock:
            thread_id = self._thread_id
            post_message = self._post_message
        if thread_id is not None and post_message is not None:
            with contextlib.suppress(Exception):
                post_message(thread_id, self._WM_QUIT, 0, 0)

    def close(self) -> None:
        self.cancel()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(2.0)

    def _run(self) -> None:
        try:
            import ctypes
            import sys
            from ctypes import wintypes

            if sys.platform != "win32":
                self._ready.set()
                return

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            class MouseHookStruct(ctypes.Structure):
                _fields_ = [
                    ("pt", wintypes.POINT),
                    ("mouseData", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_void_p),
                ]

            class KeyboardHookStruct(ctypes.Structure):
                _fields_ = [
                    ("vkCode", wintypes.DWORD),
                    ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_void_p),
                ]

            hook_proc = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t,
                ctypes.c_int,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            user32.SetWindowsHookExW.argtypes = (
                ctypes.c_int,
                hook_proc,
                wintypes.HINSTANCE,
                wintypes.DWORD,
            )
            user32.SetWindowsHookExW.restype = wintypes.HHOOK
            user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)
            user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            user32.CallNextHookEx.argtypes = (
                wintypes.HHOOK,
                ctypes.c_int,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            user32.CallNextHookEx.restype = ctypes.c_ssize_t
            user32.GetMessageW.argtypes = (
                ctypes.POINTER(wintypes.MSG),
                wintypes.HWND,
                wintypes.UINT,
                wintypes.UINT,
            )
            user32.GetMessageW.restype = wintypes.BOOL
            user32.PostThreadMessageW.argtypes = (
                wintypes.DWORD,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            user32.PostThreadMessageW.restype = wintypes.BOOL
            user32.PeekMessageW.argtypes = (
                ctypes.POINTER(wintypes.MSG),
                wintypes.HWND,
                wintypes.UINT,
                wintypes.UINT,
                wintypes.UINT,
            )
            user32.PeekMessageW.restype = wintypes.BOOL
            kernel32.GetCurrentThreadId.argtypes = ()
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD
            kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
            kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

            thread_id = kernel32.GetCurrentThreadId()
            selected: list[tuple[int, int] | None] = [None]
            cancelled = False

            def finish(point: tuple[int, int] | None) -> None:
                nonlocal cancelled
                selected[0] = point
                cancelled = point is None
                self._stop.set()
                user32.PostThreadMessageW(thread_id, self._WM_QUIT, 0, 0)

            def mouse_proc(n_code: int, w_param: int, l_param: int) -> int:
                try:
                    if n_code == self._HC_ACTION and w_param in {
                        self._WM_LBUTTONDOWN,
                        self._WM_RBUTTONDOWN,
                    }:
                        info = ctypes.cast(
                            l_param,
                            ctypes.POINTER(MouseHookStruct),
                        ).contents
                        if w_param == self._WM_LBUTTONDOWN:
                            finish((info.pt.x, info.pt.y))
                        else:
                            finish(None)
                        return 1
                except Exception:
                    LOG.exception("Windows mouse picker hook failed")
                return user32.CallNextHookEx(None, n_code, w_param, l_param)

            def keyboard_proc(n_code: int, w_param: int, l_param: int) -> int:
                try:
                    if n_code == self._HC_ACTION and w_param == self._WM_KEYDOWN:
                        info = ctypes.cast(
                            l_param,
                            ctypes.POINTER(KeyboardHookStruct),
                        ).contents
                        if info.vkCode == self._VK_ESCAPE:
                            finish(None)
                            return 1
                except Exception:
                    LOG.exception("Windows keyboard picker hook failed")
                return user32.CallNextHookEx(None, n_code, w_param, l_param)

            mouse_hook = None
            keyboard_hook = None
            mouse_callback = hook_proc(mouse_proc)
            keyboard_callback = hook_proc(keyboard_proc)
            try:
                module = kernel32.GetModuleHandleW(None)
                mouse_hook = user32.SetWindowsHookExW(
                    self._WH_MOUSE_LL,
                    mouse_callback,
                    module,
                    0,
                )
                keyboard_hook = user32.SetWindowsHookExW(
                    self._WH_KEYBOARD_LL,
                    keyboard_callback,
                    module,
                    0,
                )
                if not mouse_hook:
                    LOG.warning("Could not install the Windows mouse picker hook")
                    return
                message = wintypes.MSG()
                user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
                with self._lock:
                    self._thread_id = thread_id
                    self._post_message = user32.PostThreadMessageW
                self._ready_result = True
                self._ready.set()

                while not self._stop.is_set():
                    result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                    if result <= 0:
                        break
                if cancelled:
                    selected[0] = None
            finally:
                with contextlib.suppress(Exception):
                    if mouse_hook:
                        user32.UnhookWindowsHookEx(mouse_hook)
                with contextlib.suppress(Exception):
                    if keyboard_hook:
                        user32.UnhookWindowsHookEx(keyboard_hook)
                with self._lock:
                    self._thread_id = None
                    self._post_message = None
                self._ready.set()
                if self._ready_result:
                    try:
                        self._on_finished(selected[0])
                    except Exception:
                        LOG.exception("Position picker callback failed")
        except Exception:
            LOG.exception("Windows position picker failed")
            self._ready.set()
