"""Small, safe JSON store for first-run UI state.

This is intentionally narrow. General settings persistence is a later
milestone; this small store only remembers whether the welcome panel has been
dismissed. Corrupt data is treated as "not seen" instead of crashing the app.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from clickforge.services.paths import config_file

LOG = logging.getLogger(__name__)
SCHEMA_VERSION = 1


class FirstRunStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else config_file("ui-state.json")

    def _load(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("root value is not an object")
            return data
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            LOG.warning("Could not read UI state at %s: %s", self.path, exc)
            return {}

    def welcome_seen(self) -> bool:
        return bool(self._load().get("welcome_seen", False))

    def mark_welcome_seen(self) -> None:
        self._write({"schema_version": SCHEMA_VERSION, "welcome_seen": True})

    def reset_welcome(self) -> None:
        self._write({"schema_version": SCHEMA_VERSION, "welcome_seen": False})

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                tmp_name = handle.name
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except OSError as exc:
            LOG.warning("Could not write UI state at %s: %s", self.path, exc)
            if tmp_name:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
