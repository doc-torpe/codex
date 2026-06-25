"""Navegador web básico integrado con tkinter.

No requiere un navegador externo. Renderiza texto y enlaces de forma simple,
lo que permite usar el dashboard en sistemas mínimos donde solo hay Python.
"""

from __future__ import annotations

import tkinter as tk
from html.parser import HTMLParser
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
import urllib3

from .detector import LegacySSLAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _HtmlParser(HTMLParser):
    """Extrae texto plano y la posición de los enlaces de un documento HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[tuple[int, int, str]] = []
        self._current_link: Optional[tuple[int, str]] = None
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_dict = {k: v or "" for k, v in attrs}
        if tag in ("script", "style", "head"):
            self._skip += 1
            return
        if self._skip:
            return

        if tag == "a" and "href" in attrs_dict:
            self._current_link = (len("".join(self.parts)), attrs_dict["href"])
        elif tag == "br":
            self.parts.append("\n")
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")
        elif tag in ("input", "button"):
            placeholder = attrs_dict.get("value") or attrs_dict.get("placeholder") or "[input]"
            self.parts.append(f" [{placeholder}] ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "head"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return

        if tag == "a" and self._current_link:
            end = len("".join(self.parts))
            self.links.append((self._current_link[0], end, self._current_link[1]))
            self._current_link = None
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip == 0:
            self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


class SimpleBrowser(tk.Toplevel):
    """Ventana de navegador básico implementada 100% con tkinter + requests."""

    def __init__(self, parent: tk.Widget, url: str) -> None:
        super().__init__(parent)
        self.title("NetSphere Dashboard (navegador integrado)")
        self.geometry("1024x768")

        self._history: list[str] = []
        self._history_pos = -1
        self._base_url = url

        self._build_ui()
        self.load(url)

    def _build_ui(self) -> None:
        nav = tk.Frame(self, bg="#1c1c2e")
        nav.pack(fill=tk.X)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(nav, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        self.url_entry.bind("<Return>", lambda _e: self.load(self.url_var.get()))

        ttk.Button(nav, text="◀", width=3, command=self.go_back).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="▶", width=3, command=self.go_forward).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="↻", width=3, command=self.reload).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="Ir", command=lambda: self.load(self.url_var.get())).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Listo")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.pack(fill=tk.X, side=tk.BOTTOM)

        self.text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#05050f",
            fg="#d0ffd0",
            insertbackground="#00ffaa",
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.text.tag_config("link", foreground="#4dabf7", underline=True)
        self.text.tag_bind("link", "<Enter>", lambda _e: self.text.config(cursor="hand2"))
        self.text.tag_bind("link", "<Leave>", lambda _e: self.text.config(cursor=""))

    def _resolve(self, url: str) -> str:
        url = url.strip()
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self._base_url, url)

    def load(self, url: str) -> None:
        url = self._resolve(url)
        self._base_url = url
        self.url_var.set(url)
        self.status_var.set(f"Cargando {url}...")
        self.update_idletasks()

        try:
            session = requests.Session()
            session.mount("https://", LegacySSLAdapter())
            resp = session.get(url, timeout=15, verify=False)
            resp.raise_for_status()
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")
            messagebox.showerror("Error de carga", str(exc))
            return

        content_type = resp.headers.get("Content-Type", "").lower()
        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)

        if "text/html" in content_type:
            parser = _HtmlParser()
            parser.feed(resp.text)
            text = parser.get_text()
            self.text.insert("1.0", text)

            for start, end, link in parser.links:
                if start < end:
                    start_idx = f"1.0 + {start} chars"
                    end_idx = f"1.0 + {end} chars"
                    self.text.tag_add("link", start_idx, end_idx)
                    self.text.tag_bind(
                        "link",
                        "<Button-1>",
                        lambda _e, l=link: self.load(l),
                    )
        else:
            self.text.insert("1.0", resp.text[:50000])

        self.text.configure(state="disabled")
        self.status_var.set(f"{resp.status_code} {resp.reason} - {len(resp.content)} bytes")

        # Actualizar historial.
        if self._history_pos < len(self._history) - 1:
            self._history = self._history[: self._history_pos + 1]
        if not self._history or self._history[-1] != url:
            self._history.append(url)
            self._history_pos += 1

    def reload(self) -> None:
        if self._history:
            self.load(self._history[self._history_pos])

    def go_back(self) -> None:
        if self._history_pos > 0:
            self._history_pos -= 1
            self.load(self._history[self._history_pos])

    def go_forward(self) -> None:
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self.load(self._history[self._history_pos])

