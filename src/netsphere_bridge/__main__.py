"""Punto de entrada de NetSphere.

Ejecutar como:
    python -m netsphere_bridge              # abrir la ventana
    python -m netsphere_bridge --gui        # forzar la ventana
    python -m netsphere_bridge --cli [IP]   # modo texto

Flags internos (usados por el ejecutable onefile para lanzar subprocesos):
    --webview-subprocess <URL>
    --qt-subprocess <URL>
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import Optional


def _log_fatal_error(exc: BaseException) -> None:
    """Escribe el traceback a un archivo y, en Windows, intenta mostrarlo."""
    try:
        log_path = Path.home() / "AirconektaTool_error.log"
        log_path.write_text(
            f"Error fatal en Airconekta Tool From NetSphere\n"
            f"{'=' * 60}\n"
            f"{traceback.format_exc()}\n",
            encoding="utf-8",
        )
    except Exception:
        pass

    try:
        # En Windows intentamos una ventana nativa si está disponible.
        if sys.platform == "win32":
            import ctypes

            msg = f"La aplicación falló al iniciar.\n\n{exc}\n\n"
            try:
                msg += f"Detalles guardados en:\n{log_path}"
            except Exception:
                pass
            ctypes.windll.user32.MessageBoxW(0, msg, "Airconekta Tool - Error", 0x10)
    except Exception:
        pass


def _run_subprocess_flag(flag: str, argv: list[str]) -> int:
    """Ejecuta el subprocess indicado por --webview-subprocess o --qt-subprocess."""
    if flag == "--webview-subprocess":
        from . import webview_subprocess

        return webview_subprocess.main(argv)
    if flag == "--qt-subprocess":
        from . import qt_subprocess

        return qt_subprocess.main(argv)
    return 2


def main(argv: Optional[list[str]] = None) -> int:
    args_list = argv if argv is not None else sys.argv[1:]

    # Flags internos de subprocess onefile; deben ir antes de argparse.
    if "--webview-subprocess" in args_list:
        idx = args_list.index("--webview-subprocess")
        return _run_subprocess_flag("--webview-subprocess", args_list[idx + 1 :])
    if "--qt-subprocess" in args_list:
        idx = args_list.index("--qt-subprocess")
        return _run_subprocess_flag("--qt-subprocess", args_list[idx + 1 :])

    parser = argparse.ArgumentParser(
        prog="netsphere-bridge",
        description="NetSphere",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abrir la ventana",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Usar el modo texto",
    )
    parser.add_argument(
        "ip",
        nargs="?",
        help="IP del equipo (solo modo texto; si no se indica, se pregunta)",
    )
    args = parser.parse_args(args_list)

    if args.cli:
        from .cli import run_cli
        return run_cli([args.ip] if args.ip else [])

    if args.gui:
        try:
            from .app import run_gui
        except ImportError as exc:
            print(
                "Error al importar la interfaz gráfica. "
                "Asegúrate de tener tkinter instalado para tu plataforma.",
                file=sys.stderr,
            )
            print(f"Detalle: {exc}", file=sys.stderr)
            return 1
        run_gui()
        return 0

    # Sin flags: intentar GUI por compatibilidad con el ejecutable original.
    try:
        from .app import run_gui
    except ImportError as exc:
        print(
            "No se pudo cargar la interfaz gráfica (tkinter no disponible). "
            "Usa --cli para el modo consola.",
            file=sys.stderr,
        )
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    run_gui()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        _log_fatal_error(exc)
        raise SystemExit(1)
