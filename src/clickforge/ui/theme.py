"""Single source of truth for the ClickForge dark theme."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# Core palette -----------------------------------------------------------------
BG = "#090E13"
BG_DEEP = "#070B0F"
PANEL = "#101720"
PANEL_ALT = "#0C1219"
PANEL_HOVER = "#141D27"
BORDER = "#1D2A37"
BORDER_STRONG = "#2A3A4A"
TEXT = "#E9F0F7"
TEXT_SECONDARY = "#A7B5C5"
MUTED = "#718096"
FAINT = "#536176"
ACCENT = "#8CE99A"
ACCENT_STRONG = "#6EE787"
ACCENT_DARK = "#0E2416"
ACCENT_TEXT = "#07110A"
DANGER = "#FF8585"
DANGER_BORDER = "#4A272D"
DANGER_BG = "#231317"
WARNING = "#F3C969"
WARNING_BG = "#241E12"
INFO = "#7DD3FC"

UI_FONT_CANDIDATES = (
    "Inter",
    "SF Pro Display",
    "Segoe UI Variable Text",
    "Segoe UI",
    "Noto Sans",
    "Cantarell",
    "DejaVu Sans",
    "Liberation Sans",
)
MONO_FONT_CANDIDATES = (
    "JetBrains Mono",
    "Cascadia Code",
    "Fira Code",
    "SF Mono",
    "Consolas",
    "DejaVu Sans Mono",
    "Liberation Mono",
)


@lru_cache(maxsize=1)
def ui_font_family() -> str:
    families = set(QFontDatabase.families())
    for candidate in UI_FONT_CANDIDATES:
        if candidate in families:
            return candidate
    return "Sans Serif"


@lru_cache(maxsize=1)
def mono_font_family() -> str:
    families = set(QFontDatabase.families())
    for candidate in MONO_FONT_CANDIDATES:
        if candidate in families:
            return candidate
    return "Monospace"


def ui_font(point_size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(ui_font_family())
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


def mono_font(pixel_size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(mono_font_family())
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def _palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(PANEL_ALT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL_HOVER))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_STRONG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ACCENT_TEXT))
    palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(FAINT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(FAINT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(FAINT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(FAINT))
    return palette


def build_stylesheet() -> str:
    ui = ui_font_family()
    mono = mono_font_family()
    return f"""
* {{
    outline: none;
}}
QWidget {{
    color: {TEXT};
    font-family: "{ui}";
    font-size: 13px;
    selection-background-color: #2A5B39;
    selection-color: {TEXT};
}}
QMainWindow, QDialog, QWidget#AppRoot {{
    background: {BG};
}}
QToolTip {{
    background: {PANEL_HOVER};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 7px 9px;
    font-size: 12px;
}}
QFrame#HeaderBar {{
    background: {BG_DEEP};
    border-bottom: 1px solid {BORDER};
}}
QFrame#LogoMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #15251B, stop:1 #0B1210);
    border: 1px solid #2E4B36;
    border-radius: 12px;
}}
QFrame#FooterBar {{
    background: {BG_DEEP};
    border-top: 1px solid {BORDER};
}}
QFrame#Panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#WelcomePanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #102017, stop:0.55 {PANEL}, stop:1 {PANEL});
    border: 1px solid #274434;
    border-radius: 14px;
}}
QFrame#SummaryStrip {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#InlineNote {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}
QFrame#PreviewStateCard {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#KeyCapture {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#KeyCapture:focus {{
    border: 1px solid {ACCENT_STRONG};
    background: #0C1511;
}}
QFrame#Segmented {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}
QFrame#StatusPill {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#StatusPill[tone="accent"] {{
    background: #0F2116;
    border-color: #2A4A33;
}}
QFrame#StatusPill[tone="warning"] {{
    background: {WARNING_BG};
    border-color: #4B3C1D;
}}
QFrame#StatusPill[tone="danger"] {{
    background: {DANGER_BG};
    border-color: {DANGER_BORDER};
}}
QFrame#StatusPill[tone="idle"] {{
    background: {PANEL_ALT};
    border-color: {BORDER};
}}
QLabel#StatusText {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
    font-weight: 700;
}}
QFrame#StatusPill[tone="accent"] QLabel#StatusText {{
    color: #A8F0B4;
}}
QFrame#StatusPill[tone="warning"] QLabel#StatusText {{
    color: {WARNING};
}}
QFrame#StatusPill[tone="danger"] QLabel#StatusText {{
    color: {DANGER};
}}
QFrame#Toast {{
    background: {PANEL_HOVER};
    border: 1px solid {BORDER_STRONG};
    border-radius: 9px;
}}
QFrame#DividerV {{
    background: {BORDER};
    max-width: 1px;
    min-width: 1px;
    border: none;
}}
QFrame#DividerH {{
    background: {BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QLabel {{
    background: transparent;
}}
QLabel[role="eyebrow"] {{
    color: {MUTED};
    font-size: 10px;
    font-weight: 700;
}}
QLabel[role="panelTitle"] {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 600;
}}
QLabel[role="hero"] {{
    color: {TEXT};
    font-size: 23px;
    font-weight: 600;
}}
QLabel[role="body"] {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel[role="muted"] {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel[role="faint"] {{
    color: {FAINT};
    font-size: 11px;
}}
QLabel[role="fieldLabel"] {{
    color: {MUTED};
    font-size: 9px;
    font-weight: 700;
}}
QLabel[role="summaryStrong"] {{
    color: {TEXT};
    font-size: 12px;
    font-weight: 600;
}}
QLabel[role="summaryMuted"] {{
    color: {MUTED};
    font-size: 11px;
}}
QLabel[role="sectionTitle"] {{
    color: {TEXT};
    font-size: 11px;
    font-weight: 700;
}}
QLabel[role="keycap"] {{
    background: {PANEL_ALT};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_STRONG};
    border-bottom-color: #3A4D60;
    border-radius: 5px;
    padding: 3px 7px;
    font-family: "{mono}";
    font-size: 10px;
    font-weight: 600;
}}
QLabel[role="badge"] {{
    background: {PANEL_ALT};
    color: {MUTED};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 9px;
    font-weight: 700;
}}
QLabel[role="stepNumber"] {{
    background: #12251A;
    color: {ACCENT};
    border: 1px solid #2C4C35;
    border-radius: 9px;
    font-family: "{mono}";
    font-size: 9px;
    font-weight: 700;
}}
QLabel[role="badgeAccent"] {{
    background: #12251A;
    color: #A8F0B4;
    border: 1px solid #2C4C35;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 9px;
    font-weight: 700;
}}
QLabel[role="bigStat"] {{
    color: {TEXT};
    font-family: "{mono}";
    font-size: 40px;
    font-weight: 600;
}}
QLabel[role="statValue"] {{
    color: {TEXT};
    font-family: "{mono}";
    font-size: 17px;
    font-weight: 600;
}}
QLabel[role="accent"] {{
    color: {ACCENT};
}}
QLabel[role="warning"] {{
    color: {WARNING};
    font-size: 11px;
}}
QLabel[role="danger"] {{
    color: {DANGER};
    font-size: 11px;
}}
QLabel#BrandName {{
    color: {TEXT};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#BrandSub {{
    color: {MUTED};
    font-size: 9px;
    font-weight: 700;
}}
QLabel#VersionLabel {{
    color: {FAINT};
    font-size: 10px;
}}
QLabel#ScreenTitle {{
    color: {TEXT};
    font-size: 18px;
    font-weight: 600;
}}
QLabel#CapturedKey {{
    color: {ACCENT};
    font-family: "{mono}";
    font-size: 22px;
    font-weight: 700;
}}
QPushButton {{
    background: {PANEL_ALT};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {PANEL_HOVER};
    color: {TEXT};
    border-color: {BORDER_STRONG};
}}
QPushButton:pressed {{
    background: #0A1016;
}}
QPushButton:focus {{
    border: 1px solid {ACCENT_STRONG};
}}
QPushButton:disabled {{
    color: {FAINT};
    background: #0B1118;
    border-color: #19242F;
}}
QPushButton#PrimaryAction {{
    background: {ACCENT};
    color: {ACCENT_TEXT};
    border: 1px solid {ACCENT};
    border-radius: 10px;
    padding: 0 22px;
    font-size: 13px;
    font-weight: 800;
}}
QPushButton#PrimaryAction:hover {{
    background: #A5F2B1;
    border-color: #A5F2B1;
}}
QPushButton#PrimaryAction:pressed {{
    background: #78D989;
    border-color: #78D989;
}}
QPushButton#PrimaryAction:focus {{
    border: 2px solid #D8FFDF;
}}
QPushButton#PrimaryAction:disabled {{
    background: #142019;
    color: #5F8168;
    border: 1px solid #24372B;
}}
QPushButton#DangerAction {{
    background: {DANGER_BG};
    color: {DANGER};
    border: 1px solid {DANGER_BORDER};
    border-radius: 10px;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#DangerAction:hover {{
    background: #30191E;
    border-color: #6B353D;
    color: #FFA3A3;
}}
QPushButton#DangerAction:focus {{
    border: 1px solid {DANGER};
}}
QPushButton#DangerAction:disabled {{
    background: #130E10;
    color: #5B3B40;
    border-color: #2A1A1E;
}}
QPushButton#GhostButton {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 12px;
}}
QPushButton#GhostButton:hover {{
    background: {PANEL_HOVER};
    color: {TEXT};
    border-color: {BORDER_STRONG};
}}
QPushButton#AccentGhostButton {{
    background: transparent;
    color: {ACCENT};
    border: 1px solid #2C4C35;
    border-radius: 8px;
    padding: 7px 12px;
}}
QPushButton#AccentGhostButton:hover {{
    background: #12251A;
    border-color: #3C6849;
}}
QPushButton#LinkButton {{
    background: transparent;
    color: {MUTED};
    border: none;
    padding: 3px 2px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#LinkButton:hover {{
    color: {TEXT};
}}
QPushButton#Chip {{
    background: transparent;
    color: {MUTED};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 4px 10px;
    font-family: "{mono}";
    font-size: 10px;
    font-weight: 600;
}}
QPushButton#Chip:hover {{
    background: {PANEL_HOVER};
    color: {TEXT_SECONDARY};
    border-color: {BORDER_STRONG};
}}
QPushButton#Chip[active="true"] {{
    background: #12251A;
    color: {ACCENT};
    border-color: #2D5137;
}}
QToolButton#IconButton {{
    background: transparent;
    color: {MUTED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0;
}}
QToolButton#IconButton:hover {{
    background: {PANEL_HOVER};
    color: {TEXT};
    border-color: {BORDER};
}}
QToolButton#IconButton:focus {{
    border-color: {ACCENT_STRONG};
}}
QToolButton#IconButton:disabled {{
    color: {FAINT};
}}
QRadioButton[segment="true"] {{
    background: transparent;
    color: {MUTED};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QRadioButton[segment="true"]::indicator {{
    width: 0;
    height: 0;
}}
QRadioButton[segment="true"]:hover {{
    color: {TEXT_SECONDARY};
    background: #121B24;
}}
QRadioButton[segment="true"]:checked {{
    background: #1A2531;
    color: {TEXT};
    border: 1px solid #2B3B4C;
}}
QRadioButton[segment="true"]:focus {{
    border: 1px solid {ACCENT_STRONG};
}}
QRadioButton[segment="true"]:disabled {{
    color: {FAINT};
}}
QSpinBox, QLineEdit {{
    background: {PANEL_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 9px;
    font-family: "{mono}";
    font-size: 12px;
    font-weight: 500;
}}
QSpinBox:hover, QLineEdit:hover {{
    border-color: {BORDER_STRONG};
}}
QSpinBox:focus, QLineEdit:focus {{
    border: 1px solid {ACCENT_STRONG};
    background: #0A1117;
}}
QSpinBox:disabled, QLineEdit:disabled {{
    color: {FAINT};
    background: #0A0F14;
    border-color: #17212B;
}}
QLineEdit[readOnly="true"] {{
    color: {TEXT_SECONDARY};
}}
QProgressBar {{
    background: {PANEL_ALT};
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QWidget#ScrollBody {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 1px 2px 0;
}}
QScrollBar::handle:vertical {{
    background: #253341;
    min-height: 28px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #34475A;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: {PANEL_ALT};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    border: none;
    padding: 9px 16px;
    margin-right: 4px;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {TEXT_SECONDARY};
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QMenu {{
    background: {PANEL_HOVER};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{
    padding: 7px 22px 7px 12px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: #1D2A37;
}}
QMessageBox, QInputDialog {{
    background: {PANEL};
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setPalette(_palette())
    app.setFont(ui_font())
    app.setStyleSheet(build_stylesheet())


def repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
