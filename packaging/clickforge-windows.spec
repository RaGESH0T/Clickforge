# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "ClickForge"

a = Analysis(
    [str(ROOT / "scripts" / "launch.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (
            str(ROOT / "src" / "clickforge" / "resources"),
            "clickforge/resources",
        )
    ],
    hiddenimports=["clickforge.backends.windows"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "packaging" / "clickforge.ico"),
)
