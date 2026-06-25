#!/usr/bin/env python3
"""Proceso hijo para ejecutar Qt WebEngine sin bloquear tkinter."""

from __future__ import annotations

import sys

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: qt_subprocess.py <URL>", file=sys.stderr)
        return 1

    url = sys.argv[1]
    try:
        app = QApplication(sys.argv)
        view = QWebEngineView()
        view.setUrl(QUrl(url))
        view.setWindowTitle("NetSphere Dashboard")
        view.resize(1280, 800)
        view.show()
        return app.exec()
    except Exception as exc:
        print(f"Error iniciando Qt WebEngine: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
