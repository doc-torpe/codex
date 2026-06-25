#!/usr/bin/env python3
"""Script de build para crear ejecutables con PyInstaller.

Genera un ejecutable standalone por sistema operativo:
  - Windows: dist/AirconektaToolFromNetSphere.exe
  - macOS:   dist/AirconektaToolFromNetSphere.app
  - Linux:   dist/AirconektaToolFromNetSphere

Uso:
    python build.py
"""

from __future__ import annotations

import os
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


def build() -> int:
    clean_dist()

    plat = get_platform()
    if plat == "windows":
        exe_name = f"{APP_NAME}.exe"
        console = False  # GUI app en Windows
    elif plat == "macos":
        exe_name = APP_NAME
        console = False
    elif plat == "linux":
        exe_name = APP_NAME
        console = True  # Linux puede mostrar logs útiles
    else:
        print(f"Sistema no soportado: {plat}")
        return 1

    # Incluir subprocess helpers del navegador integrado.
    add_data = []
    for script in ["webview_subprocess.py", "qt_subprocess.py"]:
        src = Path("src/netsphere_bridge") / script
        if src.exists():
            add_data.extend(["--add-data", f"{src}:netsphere_bridge"])

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
        "--hidden-import",
        "netsphere_bridge.app",
        "--hidden-import",
        "netsphere_bridge.cli",
        "--hidden-import",
        "netsphere_bridge.browser",
        "--hidden-import",
        "netsphere_bridge.webview_browser",
        "--hidden-import",
        "netsphere_bridge.qt_browser",
        "--hidden-import",
        "netsphere_bridge.webview_subprocess",
        "--hidden-import",
        "netsphere_bridge.qt_subprocess",
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "webview",
        "--hidden-import",
        "webview.platforms.qt",
        "--hidden-import",
        "PySide6",
        "--hidden-import",
        "PySide6.QtWebEngineWidgets",
        *add_data,
        ENTRY_POINT,
    ]

    print(f"Building for {plat}...")
    print(" ".join(cmd))
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Build fallido.")
        return result.returncode

    print(f"\nBuild exitoso. Artifacts en dist/")
    for item in Path("dist").iterdir():
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
