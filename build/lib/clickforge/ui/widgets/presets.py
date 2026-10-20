"""Built-in quick presets panel."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clickforge.services.presets import BUILTIN_PRESETS, Preset
from clickforge.ui.widgets.common import Badge, PresetButton


class PresetsPanel(QFrame):
    preset_applied = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAccessibleName("Built-in click presets")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        header = QHBoxLayout()
        eyebrow = QLabel("QUICK PRESETS")
        eyebrow.setProperty("role", "eyebrow")
        header.addWidget(eyebrow)
        header.addStretch(1)
        header.addWidget(Badge("BUILT-IN"))
        layout.addLayout(header)

        self.buttons: dict[str, PresetButton] = {}
        for preset in BUILTIN_PRESETS:
            button = PresetButton(preset.name, preset.summary)
            button.setObjectName(f"preset_{preset.key}")
            button.clicked.connect(lambda checked=False, p=preset: self._apply(p))
            self.buttons[preset.key] = button
            layout.addWidget(button)

        hint = QLabel("Apply a starting point, then fine-tune below.")
        hint.setProperty("role", "faint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

    def _apply(self, preset: Preset) -> None:
        self.preset_applied.emit(preset)
