"""Gestión de certificados autofirmados para el proxy local HTTPS."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from . import config


def generate_cert() -> None:
    """Genera un certificado RSA autofirmado en un directorio temporal."""
    config.TMP_DIR = Path(tempfile.mkdtemp(prefix="netsphere-bridge-"))
    config.cert_file = config.TMP_DIR / "proxy.crt"
    config.key_file = config.TMP_DIR / "proxy.key"

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "netsphere.local"),
    ])
    now = datetime.now(timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )

    config.key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    config.cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
