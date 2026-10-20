"""Detect whether desktop automation can work on the current session.

The UI uses this to explain limitations before a session starts. Detection is
kept framework-independent so it can be tested without a display server.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    backend_id: str
    display_name: str
    available: bool
    session_type: str
    supports_global_hotkeys: bool = False
    supports_position_capture: bool = False
    reason: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status_label(self) -> str:
        return "Available" if self.available else "Unavailable"


def detect_capabilities(
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> BackendCapabilities:
    env = os.environ if environ is None else environ
    platform_name = platform_name or sys.platform

    if platform_name.startswith("win"):
        return BackendCapabilities(
            backend_id="windows-sendinput",
            display_name="Windows SendInput",
            available=True,
            session_type="windows",
            supports_global_hotkeys=True,
            supports_position_capture=True,
            notes=(
                "Per-monitor DPI awareness will be set by the Windows backend.",
                "Clicking does not require administrator privileges.",
            ),
        )

    if platform_name.startswith("linux"):
        session = env.get("XDG_SESSION_TYPE", "").lower()
        is_wayland = bool(env.get("WAYLAND_DISPLAY")) or session == "wayland"
        if is_wayland:
            return BackendCapabilities(
                backend_id="linux-wayland-unavailable",
                display_name="Wayland (not supported)",
                available=False,
                session_type="wayland",
                reason=(
                    "ClickForge v0.1 targets X11. Native Wayland blocks synthetic "
                    "input and global hotkeys for unprivileged applications."
                ),
                notes=(
                    "Log in to an X11/Xorg session to use clicking and global hotkeys.",
                    "The interface can still be opened safely on Wayland.",
                ),
            )
        if env.get("DISPLAY"):
            return BackendCapabilities(
                backend_id="linux-x11-xtest",
                display_name="X11 XTEST (python-xlib)",
                available=True,
                session_type="x11",
                supports_global_hotkeys=True,
                supports_position_capture=True,
                notes=(
                    "Global shortcuts may be captured by the desktop environment.",
                    "Some X11 window managers may intercept Escape before the app.",
                ),
            )
        return BackendCapabilities(
            backend_id="linux-no-display",
            display_name="No X11 display",
            available=False,
            session_type="none",
            reason="No DISPLAY was found, so synthetic mouse input is unavailable.",
        )

    return BackendCapabilities(
        backend_id="unsupported",
        display_name="Unsupported platform",
        available=False,
        session_type="unknown",
        reason="ClickForge supports Windows 10/11 and Linux X11 for v0.1.",
    )
