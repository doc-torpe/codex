"""Punto de entrada de NetSphere.

Ejecutar como:
    python -m netsphere_bridge              # abrir la ventana
    python -m netsphere_bridge --gui        # forzar la ventana
    python -m netsphere_bridge --cli [IP]   # modo texto
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def main(argv: Optional[list[str]] = None) -> int:
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
    args = parser.parse_args(argv)

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
    raise SystemExit(main())
