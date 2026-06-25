"""Utilidades de red y limpieza de procesos."""

from __future__ import annotations

import shutil
import socket
import time
from pathlib import Path
from typing import Optional

import psutil

from . import config


def kill_port(port: int) -> None:
    """Termina procesos que estén escuchando en el puerto indicado."""
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for conn in proc.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == port:
                    proc.kill()
        except Exception:
            continue


def tcp_open(ip: str, port: int, timeout: float = 1) -> bool:
    """Comprueba si un puerto TCP está abierto."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def wait_listen(port: int, tries: int = 300) -> bool:
    """Espera hasta que el puerto local esté escuchando."""
    for _ in range(tries):
        if tcp_open("127.0.0.1", port, 0.1):
            return True
        time.sleep(0.1)
    return False


def cleanup() -> None:
    """Detiene el proxy, cierra el túnel SSH y limpia certificados temporales."""
    config.proxy_running = False

    if config.ssh_client:
        try:
            config.ssh_client.close()
        except Exception:
            pass
        config.ssh_client = None

    if config.tunnel_server:
        try:
            config.tunnel_server.close()
        except Exception:
            pass
        config.tunnel_server = None

    time.sleep(0.8)
    kill_port(config.LOCAL_PORT)
    kill_port(config.TUNNEL_PORT)

    tmp: Optional[Path] = config.TMP_DIR
    if tmp and tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    config.TMP_DIR = None
