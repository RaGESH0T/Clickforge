"""Main single-window workflow."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QCloseEvent, QCursor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clickforge import __app_name__
from clickforge.backends import create_backend
from clickforge.backends.capabilities import BackendCapabilities, detect_capabilities
from clickforge.backends.hotkeys import create_emergency_stop_listener
from clickforge.core.engine import EngineError
from clickforge.core.models import DEFAULT_PROFILE, ClickProfile, SessionState
from clickforge.core.validation import validate_profile
from clickforge.services.first_run import FirstRunStore
from clickforge.services.presets import Preset
from clickforge.ui.dialogs.preview import PreviewDialog
from clickforge.ui.dialogs.settings import SettingsDialog
from clickforge.ui.icons import app_icon
from clickforge.ui.session_controller import SessionController
from clickforge.ui.widgets.common import Toast
from clickforge.ui.widgets.config import ClickConfigPanel
from clickforge.ui.widgets.footer import FooterBar
from clickforge.ui.widgets.header import AppHeader
from clickforge.ui.widgets.hotkeys import HotkeysPanel
from clickforge.ui.widgets.presets import PresetsPanel
from clickforge.ui.widgets.session import SessionPanel
from clickforge.ui.widgets.stats import LiveStatsPanel
from clickforge.ui.widgets.welcome import WelcomePanel

LOG = logging.getLogger(__name__)
RIGHT_RAIL_WIDTH = 338


class _HotkeyBridge(QObject):
    stop_requested = Signal()


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        capabilities: BackendCapabilities | None = None,
        first_run_store: FirstRunStore | None = None,
        session_controller: SessionController | None = None,
        show_welcome: bool | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("main_window")
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1040, 700)
        self.capabilities = capabilities or detect_capabilities()
        self.first_run_store = first_run_store or FirstRunStore()
        self.session_controller = session_controller or SessionController(
            lambda: create_backend(self.capabilities),
            self,
        )
        self.profile: ClickProfile = DEFAULT_PROFILE
        self._state = SessionState.IDLE
        self._initial_focus_applied = False
        self._hotkeys = None
        self._hotkey_bridge = _HotkeyBridge(self)
        self._hotkey_bridge.stop_requested.connect(self._emergency_stop)

        self._build_ui()
        self._wire_signals()
        self._install_shortcuts()
        self._apply_state(SessionState.IDLE)
        self._apply_profile(self.profile)
        self.session_panel.set_capabilities(self.capabilities)
        self.session_panel.set_engine_available(
            self.capabilities.available,
            self.capabilities.reason,
        )
        if not self.capabilities.supports_position_capture:
            self.config_panel.set_position_picker_available(
                False,
                self.capabilities.reason
                or "Screen position capture is unavailable on this display backend.",
            )

        if show_welcome is None:
            show_welcome = not self.first_run_store.welcome_seen()
        self.welcome_panel.setVisible(show_welcome)
        self._size_window()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        self.header = AppHeader()
        root_layout.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("ScrollBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 18, 24, 18)
        body_layout.setSpacing(16)

        self.welcome_panel = WelcomePanel()
        body_layout.addWidget(self.welcome_panel)

        columns = QHBoxLayout()
        columns.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(16)
        self.session_panel = SessionPanel()
        self.config_panel = ClickConfigPanel(self.profile)
        left.addWidget(self.session_panel)
        left.addWidget(self.config_panel)
        left.addStretch(1)

        self.right_rail = QWidget()
        self.right_rail.setFixedWidth(RIGHT_RAIL_WIDTH)
        right = QVBoxLayout(self.right_rail)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(14)
        self.stats_panel = LiveStatsPanel()
        self.presets_panel = PresetsPanel()
        self.hotkeys_panel = HotkeysPanel()
        right.addWidget(self.stats_panel)
        right.addWidget(self.presets_panel)
        right.addWidget(self.hotkeys_panel)
        right.addStretch(1)

        columns.addLayout(left, 1)
        columns.addWidget(self.right_rail, 0)
        body_layout.addLayout(columns)

        self.scroll.setWidget(body)
        root_layout.addWidget(self.scroll, 1)

        self.footer = FooterBar()
        root_layout.addWidget(self.footer)
        self.toast = Toast(self)

    def _wire_signals(self) -> None:
        self.header.help_requested.connect(self.show_welcome)
        self.header.settings_requested.connect(self.open_settings)
        self.footer.help_requested.connect(self.show_welcome)
        self.footer.settings_requested.connect(self.open_settings)
        self.welcome_panel.dismissed.connect(self.dismiss_welcome)
        self.welcome_panel.preview_requested.connect(self.open_preview)
        self.session_panel.preview_requested.connect(self.open_preview)
        self.session_panel.start_requested.connect(self._on_start_requested)
        self.session_panel.stop_requested.connect(self._on_stop_requested)
        self.hotkeys_panel.test_requested.connect(self.open_preview)
        self.config_panel.profile_changed.connect(self._apply_profile)
        self.presets_panel.preset_applied.connect(self.apply_preset)
        self.session_controller.state_changed.connect(self._on_engine_state)
        self.session_controller.stats_changed.connect(self._on_engine_stats)
        self.session_controller.finished.connect(self._on_engine_finished)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence("F1"), self, activated=self.show_welcome)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        toggle = QShortcut(QKeySequence("F6"), self, activated=self._toggle_session)
        toggle.setAutoRepeat(False)
        capture = QShortcut(QKeySequence("F7"), self, activated=self._capture_position)
        capture.setAutoRepeat(False)
        QShortcut(QKeySequence("Esc"), self, activated=self._emergency_stop)
        self._toggle_shortcut = toggle
        self._capture_shortcut = capture

    def _size_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        target_width, target_height = 1200, 900
        if screen is not None:
            available = screen.availableGeometry()
            target_width = min(target_width, max(900, available.width() - 70))
            target_height = min(target_height, max(640, available.height() - 70))
            self.resize(target_width, target_height)
            self.move(
                available.x() + max(0, (available.width() - target_width) // 2),
                available.y() + max(0, (available.height() - target_height) // 2),
            )
        else:
            self.resize(target_width, target_height)

    def _apply_profile(self, profile: ClickProfile) -> None:
        self.profile = profile
        self.session_panel.set_summary(profile)
        self.session_panel.set_start_blocked(validate_profile(profile) or "")
        self.stats_panel.set_profile(profile)

    def _apply_state(self, state: SessionState) -> None:
        self._state = state
        self.header.set_state(state)
        self.session_panel.set_state(state)
        self.stats_panel.set_state(state)
        busy = state in {
            SessionState.RUNNING,
            SessionState.PAUSED,
            SessionState.STOPPING,
        }
        self.config_panel.setEnabled(not busy)
        self.presets_panel.setEnabled(not busy)
        if self._hotkeys is not None:
            self._hotkeys.set_armed(state in {SessionState.RUNNING, SessionState.PAUSED})

    def start_global_hotkeys(self) -> bool:
        """Register the emergency stop. Safe to call once after the window is shown."""
        if not self.capabilities.supports_global_hotkeys:
            return False
        if self._hotkeys is None:
            self._hotkeys = create_emergency_stop_listener(
                self.capabilities,
                self._hotkey_bridge.stop_requested.emit,
            )
        started = self._hotkeys.start()
        self._hotkeys.set_armed(self._state in {SessionState.RUNNING, SessionState.PAUSED})
        return started

    def shutdown(self) -> None:
        """Stop the engine and release the global hotkey grab."""
        self.session_controller.close()
        if self._hotkeys is not None:
            self._hotkeys.close()
            self._hotkeys = None

    def set_session_state(self, state: SessionState) -> None:
        """Update the visual state without starting a session."""
        self._apply_state(state)

    @property
    def state(self) -> SessionState:
        return self._state

    def show_welcome(self) -> None:
        self.welcome_panel.setVisible(True)
        self.scroll.verticalScrollBar().setValue(0)
        self.welcome_panel.dismiss_button.setFocus()

    def dismiss_welcome(self) -> None:
        self.welcome_panel.setVisible(False)
        self.first_run_store.mark_welcome_seen()
        self.toast.show_message("You're all set. Explore the controls safely.")

    def open_preview(self) -> None:
        dialog = PreviewDialog(self)
        dialog.exec()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.capabilities, self)
        dialog.welcome_requested.connect(self.show_welcome)
        dialog.preview_requested.connect(lambda: self._open_preview_later())
        dialog.exec()

    def _open_preview_later(self) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self.open_preview)

    def apply_preset(self, preset: Preset) -> None:
        self.config_panel.set_profile(preset.profile)
        self.toast.show_message(f"Preset applied: {preset.name}")

    def _on_start_requested(self) -> None:
        try:
            self.session_controller.start(self.profile)
        except EngineError as exc:
            self.toast.show_message(str(exc), icon="triangle-alert", tone="warning")
            return
        self._apply_state(self.session_controller.state)
        self.toast.show_message(
            "Session started. Press Esc or Stop to cancel.",
            icon="play",
            tone="accent",
        )

    def _on_stop_requested(self) -> None:
        if self.session_controller.request_stop():
            self._apply_state(self.session_controller.state)
            return
        self.toast.show_message("No session is running.", icon="info", tone="warning")

    def _toggle_session(self) -> None:
        if self.session_controller.active:
            self._on_stop_requested()
        else:
            self._on_start_requested()

    def _capture_position(self) -> None:
        if self._state in {
            SessionState.RUNNING,
            SessionState.PAUSED,
            SessionState.STOPPING,
        }:
            return
        point = QCursor.pos()
        self.config_panel.set_target_position(point.x(), point.y())
        self.toast.show_message(
            f"Captured pointer position: {point.x():,}, {point.y():,}",
            icon="crosshair",
            tone="accent",
        )

    def _emergency_stop(self) -> None:
        if self.session_controller.active and self._state is not SessionState.STOPPING:
            self._on_stop_requested()

    def _on_engine_state(self, state: SessionState, _reason: str) -> None:
        self._apply_state(state)

    def _on_engine_stats(
        self,
        completed_clicks: int,
        elapsed_seconds: float,
        measured_rate: float,
    ) -> None:
        self.stats_panel.set_stats(completed_clicks, elapsed_seconds, measured_rate)

    def _on_engine_finished(self, state: SessionState, reason: str) -> None:
        if state is SessionState.COMPLETED:
            self.toast.show_message(reason, icon="circle-check", tone="accent")
        elif state is SessionState.ERROR:
            self.toast.show_message(reason, icon="triangle-alert", tone="danger")
        else:
            self.toast.show_message(reason, icon="square", tone="warning")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._initial_focus_applied:
            self._initial_focus_applied = True
            if self.welcome_panel.isVisible():
                self.welcome_panel.dismiss_button.setFocus()
            else:
                self.config_panel.milliseconds.spin.setFocus()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.toast.reposition()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        LOG.info("Application window closing")
        self.shutdown()
        event.accept()
