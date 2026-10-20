#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="$DATA_HOME/clickforge"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
DESKTOP_DIR="$DATA_HOME/applications"

rm -rf "$APP_DIR"
rm -f "$BIN_HOME/clickforge"
rm -f "$ICON_DIR/clickforge.svg"
rm -f "$DESKTOP_DIR/clickforge.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "ClickForge removed."
echo "Your settings and logs were left in place."
