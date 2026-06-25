#!/usr/bin/env python3
"""Proceso hijo para ejecutar pywebview sin bloquear tkinter."""

from __future__ import annotations

import sys

import webview


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: webview_subprocess.py <URL>", file=sys.stderr)
        return 1

    url = sys.argv[1]
    try:
        webview.create_window(
            "NetSphere Dashboard",
            url,
            width=1280,
            height=800,
            min_size=(800, 600),
        )
        webview.start(gui="qt")
    except Exception as exc:
        print(f"Error iniciando pywebview: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
