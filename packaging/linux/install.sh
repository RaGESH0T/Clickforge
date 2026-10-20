#!/bin/sh
set -eu

APP_NAME="ClickForge"
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="$DATA_HOME/clickforge"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
DESKTOP_DIR="$DATA_HOME/applications"

if [ "$SELF_DIR" = "$APP_DIR" ]; then
    echo "Run install.sh from the extracted tarball, not from the installed copy." >&2
    exit 1
fi

if [ ! -x "$SELF_DIR/ClickForge" ]; then
    echo "ClickForge binary not found next to install.sh." >&2
    exit 1
fi

mkdir -p "$APP_DIR" "$BIN_HOME" "$ICON_DIR" "$DESKTOP_DIR"
rm -rf "$APP_DIR/ClickForge" "$APP_DIR/_internal"
cp -a "$SELF_DIR/ClickForge" "$SELF_DIR/_internal" "$APP_DIR/"
cp -a "$SELF_DIR/LICENSE" "$SELF_DIR/README.md" "$APP_DIR/" 2>/dev/null || true
chmod 755 "$APP_DIR/ClickForge"
ln -sfn "$APP_DIR/ClickForge" "$BIN_HOME/clickforge"
install -m 644 "$SELF_DIR/clickforge.svg" "$ICON_DIR/clickforge.svg"

cat > "$DESKTOP_DIR/clickforge.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ClickForge
Comment=Safety-first desktop autoclicker
Exec="$APP_DIR/ClickForge"
Icon=clickforge
Terminal=false
Categories=Utility;
Keywords=autoclicker;clicker;automation;
StartupWMClass=ClickForge
EOF
chmod 755 "$DESKTOP_DIR/clickforge.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "$APP_NAME installed."
echo "  Application: $APP_DIR/ClickForge"
echo "  Launcher:    $BIN_HOME/clickforge"
echo "  Menu entry:  $DESKTOP_DIR/clickforge.desktop"
