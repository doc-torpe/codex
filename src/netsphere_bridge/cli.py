"""Modo consola de NetSphere."""

from __future__ import annotations

import argparse
import signal
import sys
import time
from typing import Optional

from . import config
from .cert_manager import generate_cert
from .detector import choose_proto, detect_modem_inside_antenna, detect_role_local, norm_brand
from .proxy import start_proxy
from .ssh_tunnel import start_ssh_tunnel
from .utils import cleanup, kill_port, wait_listen


def _local_url() -> str:
    scheme = "https" if config.USE_HTTPS else "http"
    return f"{scheme}://127.0.0.1:{config.LOCAL_PORT}"


def _signal_handler(signum: int, frame: Optional[object]) -> None:
    print("\n[Señal recibida] Deteniendo...")
    cleanup()
    sys.exit(0)


def _run_workflow(target: str) -> bool:
    config.modem_ip = None

    try:
        if config.USE_HTTPS:
            generate_cert()
            print("[✓] Preparando seguridad")

        kill_port(config.LOCAL_PORT)
        kill_port(config.TUNNEL_PORT)
        print("[✓] Sistema listo")

        role, brand, port = detect_role_local(target)
        print(f"[✓] Equipo detectado: {brand.title()}")

        if role == "MODEM":
            proto = choose_proto(brand, port)
            upstream = f"{proto}://{target}:{port}"
            print(f"[→] Conectando con {brand.title()}...")
            start_proxy(upstream)
            time.sleep(1.0)

        elif role == "ANTENA":
            print("[→] Buscando modem...")
            m_ip, m_port, m_brand_raw = detect_modem_inside_antenna(target)

            if not m_ip:
                raise RuntimeError("No se encontró modem detrás de la antena")

            config.modem_ip = m_ip
            m_brand = norm_brand(m_brand_raw)
            print(f"[✓] Modem {m_brand_raw.title()} encontrado")

            if not start_ssh_tunnel(target, m_ip, m_port):
                raise RuntimeError("No se pudo conectar con la antena")

            if not wait_listen(config.TUNNEL_PORT):
                raise RuntimeError("El paso no respondió a tiempo")

            proto = choose_proto(m_brand, m_port)
            upstream = f"{proto}://127.0.0.1:{config.TUNNEL_PORT}"
            print(f"[→] Conectando con {m_brand_raw.title()}...")
            start_proxy(upstream)
            time.sleep(1.0)

        else:
            raise RuntimeError("No se reconoció el equipo.")

        print("[✔] Conexión lista")
        print(f"[★] {_local_url()}")
        return True

    except Exception as e:
        print(f"[✖] Error: {e}")
        cleanup()
        return False


def run_cli(args: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="netsphere-bridge",
        description="NetSphere - modo consola",
    )
    parser.add_argument(
        "ip",
        nargs="?",
        help="IP del equipo objetivo (si no se indice, se pregunta interactivamente)",
    )
    parsed = parser.parse_args(args)

    target = parsed.ip
    if not target:
        try:
            target = input("IP del equipo: ").strip()
        except EOFError:
            print("No se proporcionó una IP.", file=sys.stderr)
            return 1

    if not target:
        print("IP no válida.", file=sys.stderr)
        return 1

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    if not _run_workflow(target):
        return 1

    print("[i] Presiona Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[i] Deteniendo...")
    finally:
        cleanup()
    return 0
