"""Detección automática de equipos de red y modems detrás de antenas."""

from __future__ import annotations

import re
from typing import Optional, Tuple

import paramiko
import requests
import urllib3
from urllib3.util.ssl_ import create_urllib3_context

from . import config
from .ssh_tunnel import configure_legacy_ssh

configure_legacy_ssh()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_ubiquiti(html: str) -> bool:
    return bool(re.search(
        r"(?i)Ubiquiti|airOS|LiteBeam|ubnt|Please login to manage your wireless device|ubnt-icon|ubnt.com",
        html,
    ))


def is_tplink(html: str) -> bool:
    return bool(re.search(
        r"(?i)TP-Link|TP-Link Technologies|tp-link|TL-WR|WR850N|TP-Link Tether|jquery\.tpInput|encrypt\.js|http://www\.tp-link\.com",
        html,
    ))


def is_zte(html: str) -> bool:
    return bool(re.search(
        r"(?i)ZTE Corporation|ZXHN|F670L|Logo_ZTE|pc-login-user|pc-login-password|pc-login-btn|pc-cloud-user|pc-cloud-password|&#70;&#54;&#55;&#48;&#76;|ZTE",
        html,
    ))


def is_huawei(html: str) -> bool:
    patterns = [
        r"(?i)Huawei Technologies",
        r"(?i)EchoLife",
        r"(?i)HG[0-9]{3,}",
        r"(?i)Cuscss/",
        r"(?i)Frm_Username|Frm_Password|LoginId",
        r"(?i)User Login|ONT Login|var G_UserLevel",
        r"(?i)var G_HttpToken|FormLogin",
        r"(?i)/html/frameset/|top\.location",
        r"(?i)Huawei web page",
        r"(?i)ssmpdes\.js",
        r"(?i)safelogin\.js",
        r"(?i)RndSecurityFormat\.js",
        r"(?i)GetRandCount\.asp",
        r"(?i)md5\.js",
        r"(?i)SSLPort|SSLHostIp",
    ]
    return any(re.search(pat, html) for pat in patterns)


def norm_brand(brand: str) -> str:
    brand = brand.lower().strip()
    if "zte" in brand:
        return "zte"
    if "huawei" in brand:
        return "huawei"
    if "tp-link" in brand or "tplink" in brand:
        return "tplink"
    if "ubiquiti" in brand or "ubnt" in brand:
        return "ubiquiti"
    return brand


def choose_proto(brand: str, port: int) -> str:
    brand = brand.lower()
    if port == 443:
        return "https"
    if brand == "huawei" and port == 80:
        return "https"
    return "http"


class LegacySSLAdapter(requests.adapters.HTTPAdapter):
    """Adaptador requests para equipos con TLS antiguo/inseguro."""

    def init_poolmanager(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        import ssl

        context = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=0")
        context.minimum_version = ssl.TLSVersion.TLSv1
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def curl_oldtls(url: str) -> str:
    try:
        session = requests.Session()
        session.mount("https://", LegacySSLAdapter())
        r = session.get(url, timeout=5, verify=False)
        return r.text[:25000]
    except Exception:
        return ""


def curl_http(url: str) -> str:
    try:
        r = requests.get(url, timeout=5)
        return r.text[:25000]
    except Exception:
        return ""


def _check_local_brand(html: str) -> Tuple[Optional[str], Optional[str]]:
    if is_ubiquiti(html):
        return ("ANTENA", "UBIQUITI")
    if is_tplink(html):
        return ("MODEM", "TP-LINK")
    if is_huawei(html):
        return ("MODEM", "HUAWEI")
    if is_zte(html):
        return ("MODEM", "ZTE")
    return (None, None)


def detect_role_local(ip: str) -> Tuple[str, str, int]:
    if tcp_open(ip, 443):
        html = curl_oldtls(f"https://{ip}/")
        if html:
            role, brand = _check_local_brand(html)
            if role and brand:
                return (role, brand, 443)

    if tcp_open(ip, 80):
        html = curl_oldtls(f"https://{ip}/")
        if html:
            role, brand = _check_local_brand(html)
            if role and brand:
                return (role, brand, 80)

        html = curl_http(f"http://{ip}/")
        if html:
            role, brand = _check_local_brand(html)
            if role and brand:
                return (role, brand, 80)

    if tcp_open(ip, 8080):
        html = curl_http(f"http://{ip}:8080/")
        if html:
            role, brand = _check_local_brand(html)
            if role and brand:
                return (role, brand, 8080)

    return ("UNKNOWN", "UNKNOWN", 0)


# Importado al final para evitar dependencia circular con utils.
from .utils import tcp_open  # noqa: E402


DETECT_MODEM_SCRIPT = r"""set -eu
get_ips(){
    ip neigh 2>/dev/null | awk '$NF!="FAILED"{print $1}' | grep -E "^192\.168\.100\." | sort -u
}
is_tplink(){
    grep -Eqi "tp-link|TP-Link Technologies|http://www\.tp-link\.com|jquery\.tpInput|encrypt\.js|TP-Link"
}
is_huawei(){
    grep -Eqi "/Cuscss/|Frm_Username|Frm_Password|Huawei web page for network configuration|HG[0-9]{3,}|Huawei Technologies|EchoLife|LoginId|G_UserLevel|G_HttpToken|FormLogin|/html/frameset/|top\.location|GetRandCount\.asp|safelogin\.js|RndSecurityFormat\.js|md5\.js|SSLPort|SSLHostIp"
}
is_zte(){
    grep -Eqi "ZTE Corporation|F670L|ZXHN|Logo_ZTE|pc-login-user|pc-login-password|pc-login-btn|pc-cloud-user|pc-cloud-password|ZTE|&#70;&#54;&#55;&#48;&#76;"
}
curl_oldtls(){
    curl -m 3 -L -s -k --tlsv1 --ciphers "DEFAULT:@SECLEVEL=0" "$1" 2>/dev/null || true
}
curl_http(){
    curl -m 2 -L -s "$1" 2>/dev/null || true
}
check_one_ip(){
    ip="$1"
    html="$(curl_oldtls "https://${ip}:443/" | head -c 25000)"
    if [ -n "$html" ]; then
        echo "$html" | is_zte && { echo "${ip}|443|ZTE"; exit 0; }
        echo "$html" | is_huawei && { echo "${ip}|443|HUAWEI"; exit 0; }
        echo "$html" | is_tplink && { echo "${ip}|443|TP-LINK"; exit 0; }
    fi
    html="$(curl_oldtls "https://${ip}:80/" | head -c 25000)"
    if [ -n "$html" ] && echo "$html" | is_huawei; then
        echo "${ip}|80|HUAWEI"; exit 0
    fi
    for p in 80 8080; do
        html="$(curl_http "http://${ip}:${p}/" | head -c 25000)"
        [ -n "$html" ] || continue
        echo "$html" | is_tplink && { echo "${ip}|${p}|TP-LINK"; exit 0; }
        echo "$html" | is_huawei && { echo "${ip}|${p}|HUAWEI"; exit 0; }
        echo "$html" | is_zte && { echo "${ip}|${p}|ZTE"; exit 0; }
    done
}
ips="$(get_ips || true)"
if [ -z "${ips}" ]; then
    for s in 1 2 254; do
        ping -c1 -W1 "192.168.100.${s}" >/dev/null 2>&1 || true
    done
    ips="$(get_ips || true)"
fi
[ -n "${ips}" ] || exit 0
for ip in ${ips}; do
    check_one_ip "$ip" || true
done
ip="192.168.100.2"
html="$(curl_oldtls "https://${ip}:443/" | head -c 25000)"
if [ -n "$html" ] && echo "$html" | is_zte; then
    echo "${ip}|443|ZTE"; exit 0
fi
exit 0
"""


def detect_modem_inside_antenna(jump: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            jump,
            username=config.SSH_USER,
            password=config.SSH_PASS,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
        stdin, stdout, stderr = client.exec_command(DETECT_MODEM_SCRIPT)
        output = stdout.read().decode().strip()
        client.close()
        if output:
            parts = output.split("|")
            if len(parts) == 3:
                return (parts[0], int(parts[1]), parts[2])
    except Exception as e:
        print(f"Error en detección SSH: {e}")
    return (None, None, None)
