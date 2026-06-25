#!/usr/bin/env python3
"""Proceso hijo para ejecutar Qt WebEngine sin bloquear tkinter.

Puede ejecutarse directamente como script o ser invocado por el ejecutable
principal mediante el flag --qt-subprocess <URL>; esto último es el único
modo compatible con un binario onefile de PyInstaller.
"""

from __future__ import annotations

import sys


def run(url: str) -> int:
    """Abre una ventana Qt WebEngine apuntando a *url*."""
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication

    try:
        app = QApplication([url])
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


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Uso: qt_subprocess.py <URL>", file=sys.stderr)
        return 1
    return run(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
