"""Platform-standard locations for local configuration and logs.

Environment overrides exist for automated tests and for a future portable
mode. Normal desktop use follows platformdirs.
"""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs

from clickforge import __app_slug__, __app_vendor__

CONFIG_DIR_ENV = "CLICKFORGE_CONFIG_DIR"
LOG_DIR_ENV = "CLICKFORGE_LOG_DIR"


def config_dir() -> Path:
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_config_dir(__app_slug__, __app_vendor__))


def log_dir() -> Path:
    override = os.environ.get(LOG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_log_dir(__app_slug__, __app_vendor__))


def config_file(name: str = "ui-state.json") -> Path:
    return config_dir() / name


def log_file(name: str = "clickforge.log") -> Path:
    return log_dir() / name
