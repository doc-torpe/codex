"""Navegador integrado real usando pywebview (motor web nativo del sistema).

Utiliza el renderizador nativo del SO:
  - Windows: Edge/WebView2
  - macOS: WKWebView
  - Linux: GTK WebKit

pywebview debe ejecutarse en el hilo principal de un proceso, así que lo
lanzamos en un subproceso separado para no bloquear la GUI de tkinter.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from . import config

try:
    import webview  # noqa: F401

    HAS_WEBVIEW = True
except Exception:  # noqa: BLE001
    HAS_WEBVIEW = False


def _local_url() -> str:
    scheme = "https" if config.USE_HTTPS else "http"
    return f"{scheme}://127.0.0.1:{config.LOCAL_PORT}"


def open_webview_browser(url: Optional[str] = None) -> tuple[bool, str]:
    """Abre el dashboard en una ventana de navegador nativo (subproceso).

    Retorna (True, "") si pudo lanzar webview, o (False, mensaje_error).
    """
    if not HAS_WEBVIEW:
        return False, "pywebview no está instalado."

    target = url or _local_url()
    script = Path(__file__).with_name("webview_subprocess.py")

    # Capturar stderr para diagnosticar fallos del subprocess.
    stderr_file = Path(tempfile.gettempdir()) / "netsphere_webview_err.log"
    try:
        stderr_file.write_text("", encoding="utf-8")
    except Exception:
        pass

    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), target],
            stdout=subprocess.DEVNULL,
            stderr=stderr_file.open("w", encoding="utf-8"),
            start_new_session=True,
        )
    except Exception as exc:
        return False, f"No se pudo lanzar el navegador: {exc}"

    # Esperar un momento para detectar si el proceso muere inmediatamente.
    time.sleep(0.5)
    if proc.poll() is not None:
        try:
            err = stderr_file.read_text(encoding="utf-8").strip()
        except Exception:
            err = ""
        if err:
            return False, f"El navegador integrado falló:\n{err}"
        return False, "El navegador integrado se cerró inmediatamente (¿faltan librerías GTK/WebKit?)."

    return True, ""
