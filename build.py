#!/usr/bin/env python3
"""Script de build para crear ejecutables portables onefile con PyInstaller.

Genera un único ejecutable por sistema operativo:
  - Windows: dist/AirconektaToolFromNetSphere.exe
  - macOS:   dist/AirconektaToolFromNetSphere
  - Linux:   dist/AirconektaToolFromNetSphere

Versiones:
    python build.py              # completa: Qt WebEngine + webview + tkinter
    python build.py --light      # ligera:  webview nativo + tkinter (sin Qt)
    python build.py --debug      # modo consola para ver errores
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "AirconektaToolFromNetSphere"
ENTRY_POINT = "src/netsphere_bridge/entry_point.py"


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


def build(debug: bool = False, light: bool = False) -> int:
    clean_dist()

    plat = get_platform()
    if plat not in ("windows", "macos", "linux"):
        print(f"Sistema no soportado: {plat}")
        return 1

    name = f"{APP_NAME}-light" if light else APP_NAME

    # En modo debug mostramos consola para diagnosticar fallos.
    # En Linux dejamos consola visible por defecto para poder ver logs.
    console = debug or plat == "linux"

    hidden_imports = [
        # Core app
        "netsphere_bridge",
        "netsphere_bridge.app",
        "netsphere_bridge.cli",
        "netsphere_bridge.browser",
        "netsphere_bridge.webview_browser",
        "netsphere_bridge.webview_subprocess",
        # GUI
        "tkinter",
        # Native webview
        "webview",
        "webview.platforms.edgechromium",
        "webview.platforms.cocoa",
        "webview.platforms.gtk",
        # Networking / crypto
        "paramiko",
        "paramiko.transport",
        "requests",
        "aiohttp",
        "cryptography",
        "urllib3",
        "idna",
        "certifi",
    ]

    collect_args: list[str] = [
        "--collect-all", "webview",
    ]

    exclude_args: list[str] = []
    if not light:
        # Versión completa: también incluimos Qt WebEngine como fallback.
        hidden_imports += [
            "netsphere_bridge.qt_browser",
            "netsphere_bridge.qt_subprocess",
            "webview.platforms.qt",
            "PySide6",
            "PySide6.QtCore",
            "PySide6.QtGui",
            "PySide6.QtWidgets",
            "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets",
            "qtpy",
            "qtpy.QtCore",
            "qtpy.QtGui",
            "qtpy.QtWidgets",
        ]
        collect_args += ["--collect-all", "PySide6", "--collect-all", "qtpy"]
    else:
        # Versión ligera: no empaquetamos Qt para reducir tamaño.
        exclude_args += [
            "--exclude-module", "PySide6",
            "--exclude-module", "qtpy",
            "--exclude-module", "shiboken6",
        ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", name,
        "--onefile",
        "--windowed" if not console else "--console",
        "--clean",
        "--noconfirm",
        "--paths", "src",
        *collect_args,
        *exclude_args,
        *[arg for name in hidden_imports for arg in ("--hidden-import", name)],
        ENTRY_POINT,
    ]

    print(f"Building {name} for {plat} (debug={debug}, light={light})...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Build fallido.")
        return result.returncode

    print("\nBuild exitoso. Artifacts en dist/")
    for item in Path("dist").iterdir():
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Airconekta Tool executable")
    parser.add_argument("--debug", action="store_true", help="Build with console for debugging")
    parser.add_argument("--light", action="store_true", help="Build lightweight version without Qt")
    args = parser.parse_args()
    raise SystemExit(build(debug=args.debug, light=args.light))
