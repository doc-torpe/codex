#!/usr/bin/env python3
"""Script de build para crear ejecutables standalone con PyInstaller.

Genera un ejecutable por sistema operativo:
  - Windows: dist/AirconektaToolFromNetSphere.exe
  - macOS:   dist/AirconektaToolFromNetSphere
  - Linux:   dist/AirconektaToolFromNetSphere

Uso:
    python build.py
    python build.py --debug       # modo consola para ver errores
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "AirconektaToolFromNetSphere"
ENTRY_POINT = "src/netsphere_bridge/__main__.py"


def get_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def clean_dist() -> None:
    dist = Path("dist")
    build = Path("build")
    if dist.exists():
        shutil.rmtree(dist)
    if build.exists():
        shutil.rmtree(build)


def build(debug: bool = False) -> int:
    clean_dist()

    plat = get_platform()
    if plat not in ("windows", "macos", "linux"):
        print(f"Sistema no soportado: {plat}")
        return 1

    # En modo debug siempre mostramos consola para ver errores.
    console = debug or plat == "linux"

    src_dir = Path("src/netsphere_bridge")
    add_data = []
    for script in ["webview_subprocess.py", "qt_subprocess.py"]:
        src = src_dir / script
        if src.exists():
            if plat == "windows":
                add_data.extend(["--add-data", f"{src};netsphere_bridge"])
            else:
                add_data.extend(["--add-data", f"{src}:netsphere_bridge"])

    hidden_imports = [
        "netsphere_bridge",
        "netsphere_bridge.app",
        "netsphere_bridge.cli",
        "netsphere_bridge.browser",
        "netsphere_bridge.webview_browser",
        "netsphere_bridge.qt_browser",
        "netsphere_bridge.webview_subprocess",
        "netsphere_bridge.qt_subprocess",
        "tkinter",
        "webview",
        "webview.platforms.qt",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "qtpy",
        "paramiko",
        "paramiko.transport",
        "requests",
        "aiohttp",
        "cryptography",
    ]

    collect_args = [
        "--collect-all", "PySide6",
        "--collect-all", "webview",
        "--collect-all", "qtpy",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--onefile",
        "--windowed" if not console else "--console",
        "--clean",
        "--noconfirm",
        "--paths", "src",
        *collect_args,
        *[arg for name in hidden_imports for arg in ("--hidden-import", name)],
        *add_data,
        ENTRY_POINT,
    ]

    print(f"Building for {plat} (debug={debug})...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Build fallido.")
        return result.returncode

    print(f"\nBuild exitoso. Artifacts en dist/")
    for item in Path("dist").iterdir():
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Airconekta Tool executable")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    args = parser.parse_args()
    raise SystemExit(build(debug=args.debug))
