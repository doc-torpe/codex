#!/usr/bin/env python3
"""Entry point para el ejecutable compilado por PyInstaller.

PyInstaller ejecuta este archivo como script principal. En lugar de repetir la
lógica de __main__.py aquí, importamos el módulo como parte del paquete
netsphere_bridge; así los imports relativos dentro de __main__.py funcionan
correctamente.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_package_path() -> None:
    """Asegura que el directorio 'src' esté en sys.path para imports absolutos."""
    # En un bundle de PyInstaller sys.executable apunta al binario final;
    # __file__ apunta a entry_point.py dentro del directorio extraído.
    here = Path(__file__).resolve().parent
    src_candidate = here.parent
    if str(src_candidate) not in sys.path:
        sys.path.insert(0, str(src_candidate))


def main() -> int:
    _ensure_package_path()
    from netsphere_bridge.__main__ import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
