#!/usr/bin/env python3
"""Proceso hijo para ejecutar pywebview sin bloquear tkinter.

Puede ejecutarse directamente como script o ser invocado por el ejecutable
principal mediante el flag --webview-subprocess <URL>; esto último es el
único modo compatible con un binario onefile de PyInstaller.
"""

from __future__ import annotations

import sys


def run(url: str) -> int:
    """Abre una ventana pywebview apuntando a *url*."""
    import webview

    try:
        webview.create_window(
            "NetSphere Dashboard",
            url,
            width=1280,
            height=800,
            min_size=(800, 600),
        )
        # Dejamos que webview elija el backend nativo del sistema:
        # Windows -> Edge/WebView2, macOS -> WKWebView, Linux -> GTK WebKit.
        webview.start()
    except Exception as exc:
        print(f"Error iniciando pywebview: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Uso: webview_subprocess.py <URL>", file=sys.stderr)
        return 1
    return run(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
