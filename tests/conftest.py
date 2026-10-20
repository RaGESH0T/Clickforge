"""Shared pytest setup. Tests never touch real user settings."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_app_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("CLICKFORGE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("CLICKFORGE_LOG_DIR", str(tmp_path / "logs"))


@pytest.fixture(scope="session", autouse=True)
def release_icon_cache(qapp):
    from clickforge.ui.icons import clear_icon_cache

    yield
    clear_icon_cache()
