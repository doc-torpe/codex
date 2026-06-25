"""Proxy HTTPS local basado en aiohttp."""

from __future__ import annotations

import asyncio
import re
import ssl
import threading
import urllib.parse
from typing import Optional

import aiohttp
from aiohttp import web

from . import config


def _original_host(parsed: urllib.parse.ParseResult) -> str:
    is_tunnel = str(config.TUNNEL_PORT) in parsed.netloc
    if is_tunnel and config.modem_ip:
        return config.modem_ip
    if ":" in parsed.netloc:
        return parsed.netloc.split(":")[0]
    return parsed.netloc


async def proxy_handler(request: web.Request) -> web.Response:
    if not config.upstream_url:
        return web.Response(status=500, text="Upstream no configurado")

    parsed = urllib.parse.urlparse(config.upstream_url)
    target_path = str(request.rel_url.path) or "/"
    target_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        target_path,
        "",
        request.rel_url.query_string,
        "",
    ))

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "connection")
    }

    original_host = _original_host(parsed)
    original_proto = parsed.scheme

    headers["Host"] = original_host
    headers["Origin"] = f"{original_proto}://{original_host}"
    headers["Referer"] = f"{original_proto}://{original_host}{request.rel_url}"
    headers["X-Forwarded-Proto"] = original_proto
    headers["X-Forwarded-Host"] = original_host
    headers["X-Real-IP"] = "127.0.0.1"
    headers["X-Forwarded-For"] = "127.0.0.1"
    headers["Connection"] = "keep-alive"
    headers["Proxy-Connection"] = "keep-alive"

    ssl_ctx: Optional[ssl.SSLContext] = None
    if parsed.scheme == "https":
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1
        ssl_ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        ssl_ctx.set_alpn_protocols(["http/1.1"])
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
                new_headers: dict[str, str] = {}
                for k, v in resp.headers.items():
                    if k.lower() == "location":
                        local_scheme = "https" if config.USE_HTTPS else "http"
                        v = re.sub(
                            f"(?i)^{re.escape(original_proto)}://{re.escape(parsed.netloc)}(:\\d+)?",
                            f"{local_scheme}://127.0.0.1:{config.LOCAL_PORT}",
                            v,
                        )
                    if k.lower() not in ("content-encoding", "transfer-encoding", "connection"):
                        new_headers[k] = v

                body = await resp.read()
                return web.Response(status=resp.status, headers=new_headers, body=body)
    except Exception as e:
        return web.Response(status=502, text=str(e))


async def start_proxy_async(upstream: str) -> None:
    config.upstream_url = upstream
    config.proxy_running = True

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", proxy_handler)

    ssl_context: Optional[ssl.SSLContext] = None
    if config.USE_HTTPS:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=str(config.cert_file),
            keyfile=str(config.key_file),
        )
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    runner = web.AppRunner(app)
    config.runner = runner
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.LOCAL_PORT, ssl_context=ssl_context)
    await site.start()

    scheme = "https" if config.USE_HTTPS else "http"
    print(f"[Proxy activo] {scheme}://127.0.0.1:{config.LOCAL_PORT}/ → {upstream}")
    while config.proxy_running:
        await asyncio.sleep(1)

    if runner is config.runner:
        await runner.cleanup()
        config.runner = None


def start_proxy(upstream: str) -> None:
    threading.Thread(
        target=lambda: asyncio.run(start_proxy_async(upstream)),
        daemon=True,
    ).start()
