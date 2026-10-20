"""Live session statistics panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from clickforge.core.formatting import format_count, format_duration, format_rate
from clickforge.core.models import ClickProfile, RepeatMode, SessionState
from clickforge.ui import theme
from clickforge.ui.widgets.common import Badge, StatMetric, divider, icon_label


class LiveStatsPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAccessibleName("Live session statistics")
        self._profile: ClickProfile | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        eyebrow = QLabel("LIVE SESSION")
        eyebrow.setProperty("role", "eyebrow")
        header.addWidget(eyebrow)
        header.addStretch(1)
        self.state_badge = Badge("NOT RUNNING")
        header.addWidget(self.state_badge)
        layout.addLayout(header)

        clicks_row = QHBoxLayout()
        clicks_copy = QVBoxLayout()
        clicks_copy.setSpacing(0)
        self.clicks_value = QLabel("0")
        self.clicks_value.setObjectName("live_clicks")
        self.clicks_value.setProperty("role", "bigStat")
        self.clicks_value.setFont(theme.mono_font(36, QFont.Weight.DemiBold))
        self.clicks_value.setAccessibleName("Completed clicks")
        clicks_label = QLabel("COMPLETED CLICKS")
        clicks_label.setProperty("role", "fieldLabel")
        clicks_copy.addWidget(self.clicks_value)
        clicks_copy.addWidget(clicks_label)
        clicks_row.addLayout(clicks_copy, 1)
        clicks_row.addWidget(icon_label("activity", theme.FAINT, 20), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(clicks_row)

        layout.addWidget(divider())
        metrics = QHBoxLayout()
        metrics.setSpacing(20)
        self.elapsed_metric = StatMetric("Elapsed", "00:00.0")
        self.elapsed_metric.setObjectName("live_elapsed_metric")
        self.rate_metric = StatMetric("Measured rate", "0.0 CPS")
        self.rate_metric.setObjectName("live_rate_metric")
        metrics.addWidget(self.elapsed_metric, 1)
        metrics.addWidget(self.rate_metric, 1)
        layout.addLayout(metrics)

        progress_header = QHBoxLayout()
        progress_label = QLabel("PROGRESS")
        progress_label.setProperty("role", "fieldLabel")
        self.progress_text = QLabel("Continuous")
        self.progress_text.setProperty("role", "summaryMuted")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_header.addWidget(progress_label)
        progress_header.addStretch(1)
        progress_header.addWidget(self.progress_text)
        layout.addLayout(progress_header)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName("Session click progress")
        layout.addWidget(self.progress)

        self.note = QLabel("Completed clicks only. Timer ticks are not counted.")
        self.note.setProperty("role", "faint")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        layout.addStretch(1)

    def set_profile(self, profile: ClickProfile) -> None:
        self._profile = profile
        self.set_stats(0, 0.0, 0.0)
        if profile.repeat_mode is RepeatMode.FIXED:
            total = profile.total_planned_clicks or 0
            self.progress.setVisible(True)
            self.progress.setRange(0, max(1, total))
            self.progress.setValue(0)
            self.progress_text.setText(f"0 / {format_count(total)} clicks")
        else:
            self.progress.setVisible(False)
            self.progress_text.setText("Continuous session")

    def set_stats(
        self,
        completed_clicks: int,
        elapsed_seconds: float,
        measured_rate: float,
        *,
        total_clicks: int | None = None,
    ) -> None:
        self.clicks_value.setText(format_count(completed_clicks))
        self.elapsed_metric.set_value(format_duration(elapsed_seconds))
        self.rate_metric.set_value(f"{format_rate(measured_rate)} CPS")
        if self._profile and self._profile.repeat_mode is RepeatMode.FIXED:
            total = total_clicks
            if total is None:
                total = self._profile.total_planned_clicks or 0
            self.progress.setRange(0, max(1, total))
            self.progress.setValue(min(completed_clicks, total))
            self.progress_text.setText(
                f"{format_count(completed_clicks)} / {format_count(total)} clicks"
            )

    def set_state(self, state: SessionState) -> None:
        labels = {
            SessionState.IDLE: "NOT RUNNING",
            SessionState.READY: "READY",
            SessionState.RUNNING: "LIVE",
            SessionState.PAUSED: "PAUSED",
            SessionState.STOPPING: "STOPPING",
            SessionState.COMPLETED: "FINISHED",
            SessionState.ERROR: "STOPPED",
        }
        self.state_badge.setText(labels[state])
