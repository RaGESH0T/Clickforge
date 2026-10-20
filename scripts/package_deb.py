#!/usr/bin/env python3
"""Build a Debian binary package from the PyInstaller bundle."""

from __future__ import annotations

import gzip
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from email.utils import formatdate
from pathlib import Path

from clickforge import __version__

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "packaging" / "dist"
RELEASE = ROOT / "packaging" / "release"
BUILD = ROOT / "packaging" / "build" / "deb-root"
BUNDLE = DIST / "ClickForge"
ICON = ROOT / "src" / "clickforge" / "resources" / "app-icon.svg"
PACKAGE = "clickforge"
MAINTAINER = "ClickForge contributors"
REQUIRED_PACKAGES = (
    "libdrm2",
    "libegl1",
    "libgl1",
    "libwayland-client0",
    "libwayland-cursor0",
    "libwayland-egl1",
    "libxcb1",
)

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=ClickForge
Comment=Safety-first desktop autoclicker
Exec=clickforge
Icon=clickforge
Terminal=false
Categories=Utility;
Keywords=autoclicker;clicker;automation;
StartupWMClass=ClickForge
"""


def _architecture() -> str:
    machine = platform.machine().lower()
    return {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armhf",
        "i686": "i386",
        "i386": "i386",
    }.get(machine, machine)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _minimum_glibc() -> str | None:
    if shutil.which("readelf") is None:
        return None
    pattern = re.compile(r"Name: GLIBC_(\d+)\.(\d+)")
    highest: tuple[int, int] | None = None
    for path in BUNDLE.rglob("*"):
        if not path.is_file():
            continue
        with path.open("rb") as handle:
            if handle.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(
            ["readelf", "--version-info", str(path)],
            capture_output=True,
            check=False,
            text=True,
        )
        for match in pattern.finditer(result.stdout):
            version = (int(match.group(1)), int(match.group(2)))
            if highest is None or version > highest:
                highest = version
    return f"{highest[0]}.{highest[1]}" if highest is not None else None


def _write_gzip(path: Path, content: str) -> None:
    with path.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as archive:
        archive.write(content.encode("utf-8"))


def _normalize_permissions(package_root: Path) -> None:
    for path in package_root.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_dir() or path.stat().st_mode & 0o111:
            path.chmod(0o755)
        else:
            path.chmod(0o644)


def _stage(architecture: str) -> Path:
    package_root = BUILD / f"{PACKAGE}_{__version__}_{architecture}"
    if package_root.exists():
        shutil.rmtree(package_root)

    application = package_root / "opt" / PACKAGE
    application.parent.mkdir(parents=True)
    shutil.copytree(BUNDLE, application)

    (package_root / "usr" / "bin").mkdir(parents=True)
    os.symlink(f"/opt/{PACKAGE}/ClickForge", package_root / "usr" / "bin" / PACKAGE)

    applications = package_root / "usr" / "share" / "applications"
    applications.mkdir(parents=True)
    desktop_file = applications / f"{PACKAGE}.desktop"
    desktop_file.write_text(DESKTOP_ENTRY, encoding="utf-8")
    desktop_file.chmod(0o644)
    validator = shutil.which("desktop-file-validate")
    if validator is not None:
        result = subprocess.run(
            [validator, str(desktop_file)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("The generated desktop entry is invalid.")

    icons = package_root / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    icons.mkdir(parents=True)
    shutil.copy2(ICON, icons / f"{PACKAGE}.svg")

    documents = package_root / "usr" / "share" / "doc" / PACKAGE
    documents.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", documents / "copyright")
    _write_gzip(documents / "README.md.gz", (ROOT / "README.md").read_text(encoding="utf-8"))
    changelog = (
        f"{PACKAGE} ({__version__}) unstable; urgency=medium\n"
        "\n"
        "  * Initial release.\n"
        "\n"
        f" -- {MAINTAINER}  {formatdate(time.time(), localtime=False)}\n"
    )
    _write_gzip(documents / "changelog.Debian.gz", changelog)

    triggers = package_root / "DEBIAN" / "triggers"
    triggers.parent.mkdir(parents=True)
    triggers.write_text(
        "activate-noawait /usr/share/applications\nactivate-noawait /usr/share/icons/hicolor\n",
        encoding="utf-8",
    )
    _normalize_permissions(package_root)
    return package_root


def main() -> int:
    if not sys.platform.startswith("linux"):
        print("Debian packages must be built on Linux.", file=sys.stderr)
        return 1
    if shutil.which("dpkg-deb") is None:
        print("dpkg-deb is required to build a Debian package.", file=sys.stderr)
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

    architecture = _architecture()
    package_root = _stage(architecture)
    files = [path for path in package_root.rglob("*") if path.is_file()]
    installed_size = (sum(path.stat().st_size for path in files) + 1023) // 1024
    glibc = _minimum_glibc()
    dependencies = [f"libc6 (>= {glibc})" if glibc else "libc6", *REQUIRED_PACKAGES]
    control = (
        f"Package: {PACKAGE}\n"
        f"Version: {__version__}\n"
        f"Architecture: {architecture}\n"
        f"Maintainer: {MAINTAINER}\n"
        "Section: utils\n"
        "Priority: optional\n"
        f"Installed-Size: {installed_size}\n"
        f"Depends: {', '.join(dependencies)}\n"
        "Description: safety-first desktop autoclicker\n"
        " ClickForge repeats mouse clicks at a chosen interval on Linux X11. It\n"
        " supports fixed or follow-pointer targets, single and double clicks,\n"
        " presets, a live position picker, session limits and a global emergency\n"
        " stop. The application is local-only and requires no account or telemetry.\n"
    )
    control_file = package_root / "DEBIAN" / "control"
    control_file.write_text(control, encoding="utf-8")
    control_file.chmod(0o644)

    RELEASE.mkdir(parents=True, exist_ok=True)
    archive = RELEASE / f"{PACKAGE}_{__version__}_{architecture}.deb"
    subprocess.run(
        [
            "dpkg-deb",
            "--build",
            "--root-owner-group",
            "-Zxz",
            str(package_root),
            str(archive),
        ],
        cwd=ROOT,
        check=True,
    )
    digest = _sha256(archive)
    checksum = archive.with_name(f"{archive.name}.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")

    print(f"Debian package: {archive}")
    print(f"Architecture:   {architecture}")
    print(f"Depends:        {', '.join(dependencies)}")
    print(f"SHA-256:        {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
