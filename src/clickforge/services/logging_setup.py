"""Small rotating local log for troubleshooting. No telemetry is written."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from clickforge.services.paths import log_file

_CONFIGURED = False
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(*, verbose: bool = False, path: Path | None = None) -> Path:
    """Configure console and rotating file logging, returning the log path."""
    global _CONFIGURED
    logger = logging.getLogger("clickforge")
    if _CONFIGURED:
        return path or log_file()

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console)

    target = path or log_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            target,
            maxBytes=512 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("File logging is unavailable: %s", exc)

    _CONFIGURED = True
    return target
