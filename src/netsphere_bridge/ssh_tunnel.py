"""Túnel SSH local usando paramiko (direct-tcpip)."""

from __future__ import annotations

import socket
import threading

import paramiko
from cryptography.hazmat.primitives import hashes

from . import config


def configure_legacy_ssh() -> None:
    """Habilita algoritmos SSH antiguos para equipos Ubiquiti/legacy.

    Paramiko 3+ desactivó por seguridad algoritmos como ssh-rsa y ciphers CBC,
    pero muchos equipos de red antiguos aún los usan. Esta función los reactiva.
    """
    paramiko.Transport._preferred_kex = (
        "diffie-hellman-group-exchange-sha256",
        "diffie-hellman-group14-sha256",
        "diffie-hellman-group14-sha1",
        "diffie-hellman-group1-sha1",
        "diffie-hellman-group-exchange-sha1",
        "ecdh-sha2-nistp256",
        "ecdh-sha2-nistp384",
        "ecdh-sha2-nistp521",
        "curve25519-sha256",
        "curve25519-sha256@libssh.org",
    )
    paramiko.Transport._preferred_keys = (
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "rsa-sha2-256",
        "rsa-sha2-512",
        "ssh-rsa",
        "ssh-dss",
    )
    paramiko.Transport._preferred_ciphers = (
        "aes128-ctr",
        "aes192-ctr",
        "aes256-ctr",
        "aes128-gcm@openssh.com",
        "aes256-gcm@openssh.com",
        "aes128-cbc",
        "aes192-cbc",
        "aes256-cbc",
        "3des-cbc",
        "blowfish-cbc",
        "cast128-cbc",
        "arcfour",
        "arcfour128",
        "arcfour256",
    )
    paramiko.Transport._preferred_macs = (
        "hmac-sha2-256",
        "hmac-sha2-256-etm@openssh.com",
        "hmac-sha2-512",
        "hmac-sha2-512-etm@openssh.com",
        "hmac-sha1",
        "hmac-sha1-etm@openssh.com",
        "hmac-md5",
        "hmac-sha1-96",
        "hmac-md5-96",
    )
    paramiko.Transport._preferred_compression = ("none",)
    # Reactivar clave ssh-rsa que paramiko 3+ eliminó por seguridad.
    paramiko.Transport._key_info.update(
        {
            "ssh-rsa": paramiko.RSAKey,
            "ssh-rsa-cert-v01@openssh.com": paramiko.RSAKey,
        }
    )
    # ssh-rsa usa SHA1 para firmas; paramiko 3+ solo acepta SHA2.
    paramiko.RSAKey.HASHES["ssh-rsa"] = hashes.SHA1
    paramiko.RSAKey.HASHES["ssh-rsa-cert-v01@openssh.com"] = hashes.SHA1


configure_legacy_ssh()


def start_ssh_tunnel(ssh_host: str, remote_host: str, remote_port: int) -> bool:
    """Abre un túnel ssh_host:22 -> 127.0.0.1:TUNNEL_PORT -> remote_host:remote_port."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            ssh_host,
            username=config.SSH_USER,
            password=config.SSH_PASS,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
    except Exception as e:
        print(f"[SSH conexión fallida] {e}")
        return False

    config.ssh_client = client
    transport = client.get_transport()

    def handle_connection(local_sock: socket.socket) -> None:
        try:
            chan = transport.open_channel(
                "direct-tcpip",
                (remote_host, remote_port),
                local_sock.getpeername(),
            )

            def forward(src: socket.socket, dst: socket.socket) -> None:
                try:
                    while True:
                        try:
                            data = src.recv(4096)
                            if len(data) == 0:
                                break
                            dst.sendall(data)
                        except Exception:
                            break
                finally:
                    try:
                        src.close()
                    except Exception:
                        pass
                    try:
                        dst.close()
                    except Exception:
                        pass

            t1 = threading.Thread(target=forward, args=(local_sock, chan), daemon=True)
            t2 = threading.Thread(target=forward, args=(chan, local_sock), daemon=True)
            t1.start()
            t2.start()
        except Exception:
            local_sock.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", config.TUNNEL_PORT))
    server.listen(10)
    config.tunnel_server = server

    def acceptor() -> None:
        while True:
            try:
                sock, addr = server.accept()
                threading.Thread(
                    target=handle_connection,
                    args=(sock,),
                    daemon=True,
                ).start()
            except Exception:
                return

    threading.Thread(target=acceptor, daemon=True).start()
    return True
