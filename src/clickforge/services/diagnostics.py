"""Build a privacy-conscious diagnostic report for support requests."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6 import QtCore

from clickforge import __milestone__, __version__
from clickforge.backends.capabilities import BackendCapabilities
from clickforge.services.paths import config_dir, log_file


def redact_home(path: Path | str) -> str:
    text = str(path)
    try:
        home = str(Path.home())
    except RuntimeError:
        return text
    if home and text.startswith(home):
        return "~" + text[len(home) :]
    return text


def build_diagnostics(capabilities: BackendCapabilities) -> str:
    notes = "\n".join(f"  - {note}" for note in capabilities.notes) or "  - None"
    lines = [
        "ClickForge diagnostic report",
        "=================================",
        f"Version: {__version__} ({__milestone__})",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Operating system: {platform.platform()}",
        f"Python: {sys.version.split()[0]}",
        f"Qt: {QtCore.qVersion()}",
        f"Session type: {capabilities.session_type}",
        f"Input backend: {capabilities.display_name} ({capabilities.status_label})",
        f"Global hotkeys: {'supported' if capabilities.supports_global_hotkeys else 'unavailable'}",
        (
            "Position capture: "
            f"{'supported' if capabilities.supports_position_capture else 'unavailable'}"
        ),
        f"Reason: {capabilities.reason or 'None'}",
        "Backend notes:",
        notes,
        f"Config directory: {redact_home(config_dir())}",
        f"Log file: {redact_home(log_file())}",
        "",
        "This report contains no clicks, coordinates, screenshots or account data.",
    ]
    return "\n".join(lines)
