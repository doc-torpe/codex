"""Configuración centralizada de NetSphere Bridge Proxy.

Todas las constantes sensibles pueden sobreescribirse mediante variables de
entorno, lo que facilita distribuir la app sin hardcodear credenciales.
"""

from __future__ import annotations

import os

SSH_USER = os.environ.get("NETSPHERE_SSH_USER", "airconekta")
SSH_PASS = os.environ.get("NETSPHERE_SSH_PASS", "airconekta.01@")

LOCAL_PORT = int(os.environ.get("NETSPHERE_LOCAL_PORT", "6060"))
TUNNEL_PORT = int(os.environ.get("NETSPHERE_TUNNEL_PORT", "8443"))
USE_HTTPS = os.environ.get("NETSPHERE_USE_HTTPS", "0") == "1"

# Estado global compartido entre módulos.
TMP_DIR = None
cert_file = None
key_file = None
upstream_url = None
proxy_running = False
ssh_client = None
tunnel_server = None
modem_ip = None
gui_running = False
runner = None

EASTER_EGG_TEXT = "Config By JAEG\nJair Elizondo\n+52 1 322 243 9782"
