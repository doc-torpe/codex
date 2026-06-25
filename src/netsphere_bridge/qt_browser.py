"""Navegador integrado basado en Qt WebEngine (Chromium).

Esta alternativa no depende de WebKitGTK; utiliza el motor Chromium de
PySide6-WebEngine. Se ejecuta en un subproceso para no bloquear tkinter.
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
    import PySide6  # noqa: F401

    HAS_QT = True
except Exception:  # noqa: BLE001
    HAS_QT = False


def _local_url() -> str:
    scheme = "https" if config.USE_HTTPS else "http"
    return f"{scheme}://127.0.0.1:{config.LOCAL_PORT}"


def open_qt_browser(url: Optional[str] = None) -> tuple[bool, str]:
    """Abre el dashboard en una ventana Qt WebEngine (subproceso).

    Retorna (True, "") si pudo lanzar Qt, o (False, mensaje_error).
    """
    if not HAS_QT:
        return False, "PySide6 no está instalado."

    target = url or _local_url()
    script = Path(__file__).with_name("qt_subprocess.py")

    stderr_file = Path(tempfile.gettempdir()) / "netsphere_qt_err.log"
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
        return False, f"No se pudo lanzar el navegador Qt: {exc}"

    time.sleep(0.5)
    if proc.poll() is not None:
        try:
            err = stderr_file.read_text(encoding="utf-8").strip()
        except Exception:
            err = ""
        if err:
            return False, f"Qt WebEngine falló:\n{err}"
        return False, "Qt WebEngine se cerró inmediatamente."

    return True, ""
