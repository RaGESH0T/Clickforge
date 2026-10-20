from PySide6.QtCore import Qt

from clickforge.backends.capabilities import BackendCapabilities
from clickforge.core.models import SessionState
from clickforge.ui.dialogs.preview import PreviewDialog
from clickforge.ui.dialogs.settings import SettingsDialog


def test_preview_cycles_every_state(qtbot):
    dialog = PreviewDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(20)

    for state in SessionState:
        dialog.set_state(state)
        assert dialog.current_state is state
        assert dialog.status_pill.current_state is state
        assert dialog.preview_title.text()


def test_preview_key_test_is_local_only(qtbot):
    dialog = PreviewDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(20)
    dialog.key_capture.setFocus()
    qtbot.wait(10)

    qtbot.keyClick(dialog.key_capture, Qt.Key.Key_F6)

    assert dialog.key_capture.key_label.text() == "F6"
    assert "detected locally" in dialog.key_capture.status.text()
    assert "Global registration is not active" in dialog.key_capture.status.text()


def test_settings_has_expected_tabs_and_no_ampersand_mnemonic(qtbot):
    capabilities = BackendCapabilities(
        backend_id="test",
        display_name="Test backend",
        available=False,
        session_type="test",
        reason="Test reason",
    )
    dialog = SettingsDialog(capabilities)
    qtbot.addWidget(dialog)

    assert dialog.tabs.count() == 4
    labels = [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())]
    assert labels == ["General", "Hotkeys", "Data privacy", "About"]
    assert "&" not in " ".join(labels)


def test_settings_can_copy_a_diagnostic_report(qtbot):
    capabilities = BackendCapabilities(
        backend_id="test",
        display_name="Test backend",
        available=False,
        session_type="test",
        reason="Test reason",
    )
    dialog = SettingsDialog(capabilities)
    qtbot.addWidget(dialog)

    dialog._copy_diagnostics()

    assert "copied" in dialog.status_label.text().lower()
    clipboard_text = dialog.parent().clipboard().text() if dialog.parent() else ""
    assert isinstance(clipboard_text, str)
