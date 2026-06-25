#!/usr/bin/env python3
"""Wrapper local para ejecutar NetSphere Bridge Proxy directamente.

Uso:
    python app.py -gui
    python app.py -cli [IP]
    python app.py --cli [IP]
"""

from __future__ import annotations

import sys

from netsphere_bridge.__main__ import main


if __name__ == "__main__":
    # Acepta tanto -gui/-cli como --gui/--cli, pero deja IPs/argumentos posicionales intactos.
    argv = []
    for arg in sys.argv[1:]:
        if arg.startswith("-") and not arg.startswith("--"):
            argv.append(f"--{arg[1:]}")
        else:
            argv.append(arg)
    raise SystemExit(main(argv))
