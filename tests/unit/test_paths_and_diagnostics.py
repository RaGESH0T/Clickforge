from pathlib import Path

from clickforge import __version__
from clickforge.backends.capabilities import BackendCapabilities
from clickforge.services.diagnostics import build_diagnostics, redact_home
from clickforge.services.paths import config_dir, config_file, log_dir, log_file


def test_environment_overrides_are_used(monkeypatch, tmp_path):
    config = tmp_path / "cfg"
    logs = tmp_path / "logs"
    monkeypatch.setenv("CLICKFORGE_CONFIG_DIR", str(config))
    monkeypatch.setenv("CLICKFORGE_LOG_DIR", str(logs))

    assert config_dir() == config
    assert log_dir() == logs
    assert config_file("custom.json") == config / "custom.json"
    assert log_file("custom.log") == logs / "custom.log"


def test_redact_home_replaces_the_home_prefix():
    path = Path.home() / "Documents" / "clickforge"
    assert redact_home(path) == "~/Documents/clickforge"


def test_diagnostics_contains_context_but_no_user_content():
    capabilities = BackendCapabilities(
        backend_id="test",
        display_name="Test backend",
        available=False,
        session_type="test",
        reason="Test reason",
        notes=("Note one",),
    )
    report = build_diagnostics(capabilities)
    assert "ClickForge diagnostic report" in report
    assert __version__ in report
    assert "Test backend (Unavailable)" in report
    assert "Test reason" in report
    assert "Note one" in report
    assert "no clicks, coordinates, screenshots" in report
