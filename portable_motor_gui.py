"""
NetSphere Bridge Proxy For Airconekta
GUI oscura - detección automática 100%
Botón Detener NO cierra la ventana (arreglado en modo antena)
Easter egg: Alt + 5
"""

import sys
import os
import time
import socket
import asyncio
import ssl
import tempfile
import shutil
import re
import urllib.parse
import threading
import webbrowser
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime, timedelta, timezone
import paramiko
import psutil
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
import aiohttp
from aiohttp import web
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

SSH_USER = 'airconekta'
SSH_PASS = 'airconekta.01@'
LOCAL_PORT = 6060
TUNNEL_PORT = 8443
TMP_DIR = None
cert_file = None
key_file = None
upstream_url = None
proxy_running = False
ssh_client = None
tunnel_server = None
modem_ip = None
gui_running = False

EASTER_EGG_TEXT = 'Config By JAEG\nJair Elizondo\n+52 1 322 243 9782'


def generate_cert():
    global TMP_DIR, cert_file, key_file

    TMP_DIR = Path(tempfile.mkdtemp(prefix='netsphere-bridge-'))
    cert_file = TMP_DIR / 'proxy.crt'
    key_file = TMP_DIR / 'proxy.key'
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'netsphere.local')])
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
                x509.DNSName('localhost'),
                x509.DNSName('127.0.0.1'),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def kill_port(port: int):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port:
                    proc.kill()
        except:
            continue


def tcp_open(ip: str, port: int, timeout: float = 1) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            pass
        return True
    except:
        return False


def wait_listen(port: int, tries: int = 300) -> bool:
    for _ in range(tries):
        if tcp_open('127.0.0.1', port, 0.1):
            return True
        time.sleep(0.1)
    return False


class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers='DEFAULT:@SECLEVEL=0')
        context.minimum_version = ssl.TLSVersion.TLSv1
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


def curl_oldtls(url: str) -> str:
    try:
        session = requests.Session()
        session.mount('https://', LegacySSLAdapter())
        r = session.get(url, timeout=5, verify=False)
        return r.text[:25000]
    except:
        return ''


def curl_http(url: str) -> str:
    try:
        r = requests.get(url, timeout=5)
        return r.text[:25000]
    except:
        return ''


def is_ubiquiti(html: str) -> bool:
    return bool(re.search('(?i)Ubiquiti|airOS|LiteBeam|ubnt|Please login to manage your wireless device|ubnt-icon|ubnt.com', html))


def is_tplink(html: str) -> bool:
    return bool(re.search('(?i)TP-Link|TP-Link Technologies|tp-link|TL-WR|WR850N|TP-Link Tether|jquery\\.tpInput|encrypt\\.js|http://www\\.tp-link\\.com', html))


def is_zte(html: str) -> bool:
    return bool(re.search('(?i)ZTE Corporation|ZXHN|F670L|Logo_ZTE|pc-login-user|pc-login-password|pc-login-btn|pc-cloud-user|pc-cloud-password|&#70;&#54;&#55;&#48;&#76;|ZTE', html))


def is_huawei(html: str) -> bool:
    patterns = [
        '(?i)Huawei Technologies',
        '(?i)EchoLife',
        '(?i)HG[0-9]{3,}',
        '(?i)Cuscss/',
        '(?i)Frm_Username|Frm_Password|LoginId',
        '(?i)User Login|ONT Login|var G_UserLevel',
        '(?i)var G_HttpToken|FormLogin',
        '(?i)/html/frameset/|top\\.location',
        '(?i)Huawei web page',
        '(?i)ssmpdes\\.js',
        '(?i)safelogin\\.js',
        '(?i)RndSecurityFormat\\.js',
        '(?i)GetRandCount\\.asp',
        '(?i)md5\\.js',
        '(?i)SSLPort|SSLHostIp',
    ]
    return any(re.search(pat, html) for pat in patterns)


def norm_brand(brand: str) -> str:
    brand = brand.lower().strip()
    if 'zte' in brand:
        return 'zte'
    if 'huawei' in brand:
        return 'huawei'
    if 'tp-link' in brand or 'tplink' in brand:
        return 'tplink'
    if 'ubiquiti' in brand or 'ubnt' in brand:
        return 'ubiquiti'
    return brand


def choose_proto(brand: str, port: int) -> str:
    brand = brand.lower()
    if port == 443:
        return 'https'
    if brand == 'huawei' and port == 80:
        return 'https'
    return 'http'


def detect_role_local(ip: str) -> Tuple[str, str, int]:
    if tcp_open(ip, 443):
        html = curl_oldtls(f'https://{ip}/')
        if html:
            if is_ubiquiti(html):
                return ('ANTENA', 'UBIQUITI', 443)
            if is_tplink(html):
                return ('MODEM', 'TP-LINK', 443)
            if is_huawei(html):
                return ('MODEM', 'HUAWEI', 443)
            if is_zte(html):
                return ('MODEM', 'ZTE', 443)

    if tcp_open(ip, 80):
        html = curl_oldtls(f'https://{ip}/')
        if html:
            if is_ubiquiti(html):
                return ('ANTENA', 'UBIQUITI', 80)
            if is_tplink(html):
                return ('MODEM', 'TP-LINK', 80)
            if is_huawei(html):
                return ('MODEM', 'HUAWEI', 80)
            if is_zte(html):
                return ('MODEM', 'ZTE', 80)

        html = curl_http(f'http://{ip}/')
        if html:
            if is_ubiquiti(html):
                return ('ANTENA', 'UBIQUITI', 80)
            if is_tplink(html):
                return ('MODEM', 'TP-LINK', 80)
            if is_huawei(html):
                return ('MODEM', 'HUAWEI', 80)
            if is_zte(html):
                return ('MODEM', 'ZTE', 80)

    if tcp_open(ip, 8080):
        html = curl_http(f'http://{ip}:8080/')
        if html:
            if is_ubiquiti(html):
                return ('ANTENA', 'UBIQUITI', 8080)
            if is_tplink(html):
                return ('MODEM', 'TP-LINK', 8080)
            if is_huawei(html):
                return ('MODEM', 'HUAWEI', 8080)
            if is_zte(html):
                return ('MODEM', 'ZTE', 8080)

    return ('UNKNOWN', 'UNKNOWN', 0)


def detect_modem_inside_antenna(jump: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    script = """
set -eu
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
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            jump,
            username=SSH_USER,
            password=SSH_PASS,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
        stdin, stdout, stderr = client.exec_command(script)
        output = stdout.read().decode().strip()
        client.close()
        if output:
            parts = output.split('|')
            if len(parts) == 3:
                return (parts[0], int(parts[1]), parts[2])
    except Exception as e:
        print(f'Error en detección SSH: {e}')
    return (None, None, None)


async def proxy_handler(request):
    if not upstream_url:
        return web.Response(status=500, text='Upstream no configurado')

    parsed = urllib.parse.urlparse(upstream_url)
    target_path = str(request.rel_url.path) or '/'
    target_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        target_path,
        '',
        request.rel_url.query_string,
        '',
    ))
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ('host', 'connection')
    }

    is_tunnel = str(TUNNEL_PORT) in parsed.netloc
    original_host = modem_ip if is_tunnel and modem_ip else parsed.netloc.split(':')[0] if ':' in parsed.netloc else parsed.netloc
    original_proto = parsed.scheme

    headers['Host'] = original_host
    headers['Origin'] = f'{original_proto}://{original_host}'
    headers['Referer'] = f'{original_proto}://{original_host}{request.rel_url}'
    headers['X-Forwarded-Proto'] = original_proto
    headers['X-Forwarded-Host'] = original_host
    headers['X-Real-IP'] = '127.0.0.1'
    headers['X-Forwarded-For'] = '127.0.0.1'
    headers['Connection'] = 'keep-alive'
    headers['Proxy-Connection'] = 'keep-alive'

    ssl_ctx = None
    if parsed.scheme == 'https':
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1
        ssl_ctx.set_ciphers('DEFAULT:@SECLEVEL=0')
        ssl_ctx.set_alpn_protocols(['http/1.1'])
        ssl_ctx.server_hostname = original_host

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=await request.read(),
                allow_redirects=False,
                ssl=ssl_ctx,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                new_headers = {}
                for k, v in resp.headers.items():
                    if k.lower() == 'location':
                        v = re.sub(
                            f'(?i)^{re.escape(original_proto)}://{re.escape(parsed.netloc)}(:\\d+)?',
                            f'https://127.0.0.1:{LOCAL_PORT}',
                            v,
                        )
                    if k.lower() not in ('content-encoding', 'transfer-encoding', 'connection'):
                        new_headers[k] = v

                body = await resp.read()
                return web.Response(status=resp.status, headers=new_headers, body=body)
    except Exception as e:
        return web.Response(status=502, text=str(e))


async def start_proxy_async(upstream: str):
    global upstream_url, proxy_running

    upstream_url = upstream
    proxy_running = True
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', proxy_handler)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', LOCAL_PORT, ssl_context=ssl_context)
    await site.start()

    print(f'[Proxy activo] https://127.0.0.1:{LOCAL_PORT}/ → {upstream}')
    while proxy_running:
        await asyncio.sleep(1)


def start_proxy(upstream: str):
    threading.Thread(
        target=lambda: asyncio.run(start_proxy_async(upstream)),
        daemon=True,
    ).start()


def start_ssh_tunnel(ssh_host: str, remote_host: str, remote_port: int):
    global ssh_client, tunnel_server

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            ssh_host,
            username=SSH_USER,
            password=SSH_PASS,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
    except Exception as e:
        print(f'[SSH conexión fallida] {e}')
        return False

    ssh_client = client
    transport = client.get_transport()

    def handle_connection(local_sock):
        try:
            chan = transport.open_channel(
                'direct-tcpip',
                (remote_host, remote_port),
                local_sock.getpeername(),
            )

            def forward(src, dst):
                try:
                    while True:
                        try:
                            data = src.recv(4096)
                            if len(data) == 0:
                                break
                            dst.sendall(data)
                        except:
                            break
                finally:
                    src.close()
                    dst.close()

            t1 = threading.Thread(target=forward, args=(local_sock, chan), daemon=True)
            t2 = threading.Thread(target=forward, args=(chan, local_sock), daemon=True)
            t1.start()
            t2.start()
        except:
            local_sock.close()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', TUNNEL_PORT))
    server.listen(10)
    tunnel_server = server

    def acceptor():
        while True:
            try:
                sock, addr = server.accept()
                threading.Thread(
                    target=handle_connection,
                    args=(sock,),
                    daemon=True,
                ).start()
            except:
                return

    threading.Thread(target=acceptor, daemon=True).start()
    return True


def cleanup():
    global proxy_running, ssh_client, tunnel_server

    proxy_running = False

    if ssh_client:
        try:
            ssh_client.close()
            ssh_client = None
        except:
            pass

    if tunnel_server:
        try:
            tunnel_server.close()
            tunnel_server = None
        except:
            pass

    time.sleep(0.8)
    kill_port(LOCAL_PORT)
    kill_port(TUNNEL_PORT)

    if TMP_DIR and TMP_DIR.exists():
        shutil.rmtree(TMP_DIR, ignore_errors=True)


class NetSphereApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NetSphere Bridge Proxy For Airconekta')
        self.geometry('520x360')
        self.resizable(False, False)
        self.configure(bg='#0d0d18')

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#0d0d18', foreground='#cccccc')
        style.configure('TLabel', background='#0d0d18', foreground='#00ffaa')
        style.configure(
            'Header.TLabel',
            background='#0d0d18',
            foreground='#00ffaa',
            font=('Segoe UI', 15, 'bold'),
        )
        style.configure(
            'TEntry',
            fieldbackground='#1c1c2e',
            foreground='#e0e0ff',
            insertcolor='#00ffaa',
        )
        style.configure('Green.TButton', background='#28a745', foreground='#000000')
        style.map('Green.TButton', background=[('active', '#218838')])
        style.configure('Red.TButton', background='#dc3545', foreground='#ffffff')
        style.map('Red.TButton', background=[('active', '#c82333')])
        style.configure('Blue.TButton', background='#007bff', foreground='#ffffff')
        style.map('Blue.TButton', background=[('active', '#0062cc')])

        self.ip_var = tk.StringVar()
        self.create_widgets()
        self.bind('<Alt-KeyPress-5>', self.show_easter_egg)
        self.protocol('WM_DELETE_WINDOW', self.on_closing)

    def create_widgets(self):
        main = tk.Frame(self, bg='#0d0d18', padx=25, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text='NetSphere Bridge Proxy For Airconekta',
            bg='#0d0d18',
            fg='#00ffaa',
            font=('Segoe UI', 15, 'bold'),
        ).pack(pady=(0, 20))

        tk.Label(
            main,
            text='IP del equipo:',
            bg='#0d0d18',
            fg='#00ffaa',
        ).pack(anchor='w')

        ttk.Entry(main, textvariable=self.ip_var, width=40).pack(pady=6, fill='x')

        self.btn_frame = tk.Frame(main, bg='#0d0d18')
        self.btn_frame.pack(pady=25)

        self.btn_start = ttk.Button(
            self.btn_frame,
            text='▶ Iniciar proxy',
            style='Green.TButton',
            command=self.start_action,
        )
        self.btn_start.pack(side='left', padx=10)

        self.btn_stop = ttk.Button(
            self.btn_frame,
            text='⏹ Detener',
            style='Red.TButton',
            command=self.stop_action,
            state='disabled',
        )

        self.btn_dashboard = ttk.Button(
            self.btn_frame,
            text='Abrir Dashboard',
            style='Blue.TButton',
            command=lambda: webbrowser.open(f'https://127.0.0.1:{LOCAL_PORT}', new=2),
            state='disabled',
        )

        tk.Label(
            main,
            text='Estado:',
            bg='#0d0d18',
            fg='#00ffaa',
            font=('Segoe UI', 11, 'bold'),
        ).pack(anchor='w')

        self.log_text = scrolledtext.ScrolledText(
            main,
            height=9,
            font=('Consolas', 11),
            bg='#05050f',
            fg='#d0ffd0',
            insertbackground='#00ffaa',
            relief='flat',
        )
        self.log_text.pack(fill='both', expand=True, pady=(6, 0))
        self.log_text.insert(tk.END, 'Listo para iniciar...\n')
        self.log_text.config(state='disabled')

    def log(self, msg: str, prefix='→'):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f'{prefix} {msg}\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.update_idletasks()

    def show_easter_egg(self, event=None):
        self.log(EASTER_EGG_TEXT, '✦')
        messagebox.showinfo('Info', EASTER_EGG_TEXT)

    def start_action(self):
        global gui_running

        if gui_running:
            self.log('Ya está en ejecución', '⚠')
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning('Atención', 'Ingresa una IP válida')
            return

        gui_running = True
        self.btn_start.pack_forget()
        self.btn_stop.pack(side='left', padx=10)
        self.btn_dashboard.pack(side='left', padx=10)
        self.btn_stop.config(state='normal')
        self.btn_dashboard.config(state='disabled')

        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

        self.log('Iniciando conexión...', '⌛')
        threading.Thread(target=self.do_work, args=(ip,), daemon=True).start()

    def do_work(self, target: str):
        global modem_ip, gui_running

        modem_ip = None

        try:
            generate_cert()
            self.log('Certificado generado', '✓')

            kill_port(LOCAL_PORT)
            kill_port(TUNNEL_PORT)
            self.log('Puertos limpiados', '✓')

            role, brand, port = detect_role_local(target)
            self.log(f'Detectado: {role} - {brand} - puerto {port}', '✓')

            if role == 'MODEM':
                proto = choose_proto(brand, port)
                upstream = f'{proto}://{target}:{port}'
                self.log(f'[MODEM] {brand.upper()} → {upstream}', '→')
                start_proxy(upstream)
                time.sleep(1.0)
                self.btn_dashboard.config(state='normal')

            elif role == 'ANTENA':
                self.log('Buscando modem detrás...', '→')
                m_ip, m_port, m_brand_raw = detect_modem_inside_antenna(target)

                if not m_ip:
                    raise RuntimeError('No se encontró modem detrás de la antena')

                modem_ip = m_ip
                m_brand = norm_brand(m_brand_raw)
                self.log(f'Encontrado: {m_brand_raw} → {m_ip}:{m_port}', '✓')

                if not start_ssh_tunnel(target, m_ip, m_port):
                    raise RuntimeError('Fallo al conectar SSH')

                if not wait_listen(TUNNEL_PORT):
                    raise RuntimeError('Túnel no levantó después de 30s')

                proto = choose_proto(m_brand, m_port)
                upstream = f'{proto}://127.0.0.1:{TUNNEL_PORT}'
                self.log(f'[TÚNEL + PROXY] {upstream}', '→')
                start_proxy(upstream)
                time.sleep(1.0)
                self.btn_dashboard.config(state='normal')

            else:
                raise RuntimeError('No se pudo detectar el equipo.')

            self.log('CONEXIÓN LOGRADA', '✔')
            self.log(f'https://127.0.0.1:{LOCAL_PORT}', '★')

        except Exception as e:
            self.log(f'ERROR: {str(e)}', '✖')
            messagebox.showerror('Error', str(e))
            self.btn_stop.pack_forget()
            self.btn_dashboard.pack_forget()
            self.btn_start.pack(side='left', padx=10)

        finally:
            gui_running = False
            if self.btn_start.winfo_exists():
                self.btn_start.config(state='normal')

    def stop_action(self):
        global gui_running

        self.log('Deteniendo conexión...', '→')
        cleanup()
        gui_running = False

        self.btn_stop.pack_forget()
        self.btn_dashboard.pack_forget()
        self.btn_start.pack(side='left', padx=10)
        self.btn_start.config(state='normal')

        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

        self.log('Conexión detenida completamente. Puedes iniciar de nuevo.', '✓')
        self.update_idletasks()

    def on_closing(self):
        if messagebox.askokcancel('Salir', '¿Cerrar NetSphere Bridge Proxy?'):
            cleanup()
            self.destroy()


if __name__ == '__main__':
    app = NetSphereApp()
    app.mainloop()
