#!/usr/bin/env python3
"""Build the Linux release tarball from the PyInstaller bundle."""

from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from clickforge import __version__

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "packaging" / "dist"
RELEASE = ROOT / "packaging" / "release"
BUNDLE = DIST / "ClickForge"
ASSETS = ROOT / "packaging" / "linux"


def _architecture() -> str:
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not sys.platform.startswith("linux"):
        print("Linux packages must be built on Linux.", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        return result.returncode
    if not (BUNDLE / "ClickForge").is_file():
        print(f"Expected bundle not found: {BUNDLE}", file=sys.stderr)
        return 1

    folder = f"ClickForge-{__version__}-linux-{_architecture()}"
    stage = RELEASE / folder
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    shutil.copytree(BUNDLE, stage, dirs_exist_ok=True)
    for name in ("START-HERE.txt", "README.md", "LICENSE"):
        shutil.copy2(ROOT / name, stage / name)
    shutil.copy2(
        ROOT / "src" / "clickforge" / "resources" / "app-icon.svg", stage / "clickforge.svg"
    )
    for name in ("install.sh", "uninstall.sh"):
        shutil.copy2(ASSETS / name, stage / name)
        (stage / name).chmod(0o755)
    (stage / "ClickForge").chmod(0o755)

    archive = RELEASE / f"{folder}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(stage, arcname=folder)
    digest = _sha256(archive)
    checksum = archive.with_name(f"{archive.name}.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")

    print(f"Linux package: {archive}")
    print(f"SHA-256:       {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
