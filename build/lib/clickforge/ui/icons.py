"""Lucide-style SVG icons rendered with an explicit theme colour."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from clickforge.ui import theme

LOG = logging.getLogger(__name__)


def _resources_dir() -> Path:
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return bundle_dir / "clickforge" / "resources"
    return Path(__file__).resolve().parent.parent / "resources"


RESOURCE_DIR = _resources_dir()
ICON_DIR = RESOURCE_DIR / "icons"
APP_ICON_PATH = RESOURCE_DIR / "app-icon.svg"

REQUIRED_ICONS = frozenset(
    {
        "activity",
        "arrow-up-right",
        "check",
        "chevron-down",
        "chevron-right",
        "circle-check",
        "circle-dot",
        "circle-help",
        "circle-x",
        "clock-3",
        "copy",
        "crosshair",
        "folder-open",
        "gauge",
        "info",
        "key-round",
        "keyboard",
        "loader-circle",
        "lock",
        "map-pin",
        "minimize-2",
        "mouse",
        "mouse-pointer-2",
        "mouse-pointer-click",
        "pause",
        "play",
        "repeat",
        "rotate-ccw",
        "scan",
        "settings",
        "shield",
        "shield-check",
        "sliders-horizontal",
        "sparkles",
        "square",
        "target",
        "terminal",
        "timer",
        "triangle-alert",
        "wifi-off",
        "x",
        "zap",
    }
)


def _svg_bytes(path: Path, color: str) -> QByteArray:
    svg = path.read_text(encoding="utf-8")
    svg = svg.replace("currentColor", color)
    return QByteArray(svg.encode("utf-8"))


@lru_cache(maxsize=512)
def _render_pixmap(name: str, color: str, size: int, scale: float = 2.0) -> QPixmap:
    path = APP_ICON_PATH if name == "__app__" else ICON_DIR / f"{name}.svg"
    if not path.exists():
        LOG.warning("Missing icon %s", path)
        path = ICON_DIR / "circle-dot.svg"

    # The app icon already carries its own palette.
    renderer = (
        QSvgRenderer(path.as_posix())
        if name == "__app__"
        else QSvgRenderer(_svg_bytes(path, color))
    )

    pixel_size = max(1, int(round(size * scale)))
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(scale)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def make_pixmap(
    name: str,
    color: str = theme.TEXT_SECONDARY,
    size: int = 18,
    scale: float = 2.0,
) -> QPixmap:
    return _render_pixmap(name, color.lower(), int(size), float(scale))


def clear_icon_cache() -> None:
    """Release cached pixmaps before the QApplication is torn down."""
    _render_pixmap.cache_clear()


def make_icon(
    name: str,
    color: str = theme.TEXT_SECONDARY,
    size: int = 18,
    disabled_color: str | None = None,
) -> QIcon:
    icon = QIcon()
    icon.addPixmap(make_pixmap(name, color, size, 1.0), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(make_pixmap(name, color, size, 2.0), QIcon.Mode.Normal, QIcon.State.Off)
    if disabled_color:
        icon.addPixmap(
            make_pixmap(name, disabled_color, size, 1.0),
            QIcon.Mode.Disabled,
            QIcon.State.Off,
        )
        icon.addPixmap(
            make_pixmap(name, disabled_color, size, 2.0),
            QIcon.Mode.Disabled,
            QIcon.State.Off,
        )
    return icon


def icon_size(size: int) -> QSize:
    return QSize(size, size)


@lru_cache(maxsize=1)
def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_render_pixmap("__app__", theme.ACCENT, size, 1.0))
    return icon
