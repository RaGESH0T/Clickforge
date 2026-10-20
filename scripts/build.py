#!/usr/bin/env python3
"""Build a self-contained desktop application with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "clickforge.spec"
DIST = ROOT / "packaging" / "dist"
WORK = ROOT / "packaging" / "build"


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('PyInstaller is required. Install it with: pip install -e ".[dev]"')
        return 1
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(DIST),
        "--workpath",
        str(WORK),
        str(SPEC),
    ]
    print("Running:", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode == 0:
        print(f"Build complete: {DIST / 'ClickForge'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
