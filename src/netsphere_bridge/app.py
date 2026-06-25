"""Interfaz gráfica de NetSphere."""

from __future__ import annotations

import threading
import time
import webbrowser

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from . import __app_name__, config
from .browser import SimpleBrowser
from .cert_manager import generate_cert
from .detector import choose_proto, detect_modem_inside_antenna, detect_role_local, norm_brand
from .proxy import start_proxy
from .qt_browser import open_qt_browser
from .ssh_tunnel import start_ssh_tunnel
from .utils import cleanup, kill_port, wait_listen
from .webview_browser import open_webview_browser


def _local_url() -> str:
    scheme = "https" if config.USE_HTTPS else "http"
    return f"{scheme}://127.0.0.1:{config.LOCAL_PORT}"


class NetSphereApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(__app_name__)
        self.geometry("580x460")
        self.resizable(False, False)
        self.configure(bg="#0b0c15")

        self._setup_styles()
        self.ip_var = tk.StringVar()
        self.create_widgets()
        self.bind("<Alt-KeyPress-5>", self.show_easter_egg)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        # Paleta moderna oscura.
        bg = "#0b0c15"
        surface = "#151725"
        accent = "#00d4aa"
        text = "#e8eaf6"
        muted = "#8b92b4"

        style.configure(".", background=bg, foreground=text)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=muted, font=("Inter", 10))
        style.configure(
            "Header.TLabel",
            background=bg,
            foreground=accent,
            font=("Inter", 18, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=bg,
            foreground=muted,
            font=("Inter", 9),
        )
        style.configure(
            "TEntry",
            fieldbackground=surface,
            foreground=text,
            insertcolor=accent,
            bordercolor="#2a2d3e",
            lightcolor="#2a2d3e",
            darkcolor="#2a2d3e",
            font=("Inter", 11),
        )
        style.map("TEntry", bordercolor=[("focus", accent)])

        # Botones planos modernos.
        style.configure(
            "Start.TButton",
            background=accent,
            foreground="#0b0c15",
            font=("Inter", 10, "bold"),
            bordercolor=accent,
            relief="flat",
        )
        style.map("Start.TButton", background=[("active", "#00b894")])

        style.configure(
            "Stop.TButton",
            background="#ff4757",
            foreground="#ffffff",
            font=("Inter", 10, "bold"),
            bordercolor="#ff4757",
            relief="flat",
        )
        style.map("Stop.TButton", background=[("active", "#e84118")])

        style.configure(
            "Action.TButton",
            background="#3742fa",
            foreground="#ffffff",
            font=("Inter", 9, "bold"),
            bordercolor="#3742fa",
            relief="flat",
        )
        style.map("Action.TButton", background=[("active", "#2f36d0")])

    def create_widgets(self) -> None:
        main = tk.Frame(self, bg="#0b0c15", padx=28, pady=22)
        main.pack(fill=tk.BOTH, expand=True)

        # Header.
        header = tk.Frame(main, bg="#0b0c15")
        header.pack(fill=tk.X, pady=(0, 18))
        tk.Label(
            header,
            text="🌐 " + __app_name__,
            bg="#0b0c15",
            fg="#00d4aa",
            font=("Inter", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Conexión remota para equipos de red",
            bg="#0b0c15",
            fg="#8b92b4",
            font=("Inter", 9),
        ).pack(anchor="w", pady=(2, 0))

        # IP input.
        input_frame = tk.Frame(main, bg="#0b0c15")
        input_frame.pack(fill=tk.X, pady=(0, 16))
        tk.Label(
            input_frame,
            text="IP del equipo",
            bg="#0b0c15",
            fg="#8b92b4",
            font=("Inter", 10),
        ).pack(anchor="w")
        self.entry_ip = ttk.Entry(
            input_frame,
            textvariable=self.ip_var,
            width=40,
        )
        self.entry_ip.pack(pady=(6, 0), fill="x")

        # Buttons.
        self.btn_frame = tk.Frame(main, bg="#0b0c15")
        self.btn_frame.pack(pady=(0, 18))

        self.btn_start = ttk.Button(
            self.btn_frame,
            text="▶  Conectar",
            style="Start.TButton",
            command=self.start_action,
            width=16,
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = ttk.Button(
            self.btn_frame,
            text="⏹  Detener",
            style="Stop.TButton",
            command=self.stop_action,
            state="disabled",
            width=14,
        )

        self.btn_dashboard = ttk.Button(
            self.btn_frame,
            text="Abrir",
            style="Action.TButton",
            command=self.open_external_dashboard,
            state="disabled",
            width=12,
        )

        self.btn_internal_dashboard = ttk.Button(
            self.btn_frame,
            text="Ventana",
            style="Action.TButton",
            command=self.open_internal_dashboard,
            state="disabled",
            width=12,
        )

        # Status log.
        tk.Label(
            main,
            text="Estado",
            bg="#0b0c15",
            fg="#8b92b4",
            font=("Inter", 10, "bold"),
        ).pack(anchor="w")

        self.log_text = scrolledtext.ScrolledText(
            main,
            height=11,
            font=("JetBrains Mono", 10),
            bg="#0e101a",
            fg="#e8eaf6",
            insertbackground="#00d4aa",
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
        )
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.config(state="disabled")

        # Tags para colorear logs.
        self.log_text.tag_config("ok", foreground="#00d4aa")
        self.log_text.tag_config("error", foreground="#ff4757")
        self.log_text.tag_config("warn", foreground="#ffa502")
        self.log_text.tag_config("info", foreground="#70a1ff")
        self.log_text.tag_config("star", foreground="#ffd32a")

        self.log("Listo. Escribe la IP del equipo y presiona Conectar.", "→")

    def log(self, msg: str, prefix: str = "→") -> None:
        self.log_text.configure(state="normal")

        tag = "info"
        if prefix in ("✓", "✔"):
            tag = "ok"
        elif prefix in ("✖", "✕"):
            tag = "error"
        elif prefix in ("⚠",):
            tag = "warn"
        elif prefix in ("★",):
            tag = "star"

        self.log_text.insert(tk.END, f"{prefix} ", tag)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    def show_easter_egg(self, event=None) -> None:  # type: ignore[no-untyped-def]
        self.log(config.EASTER_EGG_TEXT, "✦")
        messagebox.showinfo("Info", config.EASTER_EGG_TEXT)

    def start_action(self) -> None:
        if config.gui_running:
            self.log("Ya está en ejecución", "⚠")
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Atención", "Ingresa una IP válida")
            return

        config.gui_running = True
        self.btn_start.pack_forget()
        self.btn_stop.pack(side="left", padx=4)
        self.btn_dashboard.pack(side="left", padx=4)
        self.btn_internal_dashboard.pack(side="left", padx=4)
        self.btn_stop.config(state="normal")
        self.btn_dashboard.config(state="disabled")
        self.btn_internal_dashboard.config(state="disabled")

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

        self.log("Conectando...", "⌛")
        threading.Thread(target=self.do_work, args=(ip,), daemon=True).start()

    def do_work(self, target: str) -> None:
        config.modem_ip = None

        try:
            if config.USE_HTTPS:
                generate_cert()
                self.log("Preparando seguridad", "✓")

            kill_port(config.LOCAL_PORT)
            kill_port(config.TUNNEL_PORT)
            self.log("Sistema listo", "✓")

            role, brand, port = detect_role_local(target)
            brand_nice = brand.title()
            self.log(f"Equipo detectado: {brand_nice}", "✓")

            if role == "MODEM":
                self.log(f"Conectando con {brand_nice}...", "→")
                proto = choose_proto(brand, port)
                upstream = f"{proto}://{target}:{port}"
                start_proxy(upstream)
                time.sleep(1.0)
                self.btn_dashboard.config(state="normal")
                self.btn_internal_dashboard.config(state="normal")

            elif role == "ANTENA":
                self.log("Buscando modem...", "→")
                m_ip, m_port, m_brand_raw = detect_modem_inside_antenna(target)

                if not m_ip:
                    raise RuntimeError("No se encontró modem detrás de la antena")

                config.modem_ip = m_ip
                m_brand = norm_brand(m_brand_raw)
                m_brand_nice = m_brand_raw.title()
                self.log(f"Modem {m_brand_nice} encontrado", "✓")

                self.log("Abriendo paso seguro...", "→")
                if not start_ssh_tunnel(target, m_ip, m_port):
                    raise RuntimeError("No se pudo conectar con la antena")

                if not wait_listen(config.TUNNEL_PORT):
                    raise RuntimeError("El paso no respondió a tiempo")

                proto = choose_proto(m_brand, m_port)
                upstream = f"{proto}://127.0.0.1:{config.TUNNEL_PORT}"
                self.log(f"Conectando con {m_brand_nice}...", "→")
                start_proxy(upstream)
                time.sleep(1.0)
                self.btn_dashboard.config(state="normal")
                self.btn_internal_dashboard.config(state="normal")

            else:
                raise RuntimeError("No se reconoció el equipo.")

            self.log("Conexión lista", "✔")
            self.log(_local_url(), "★")

        except Exception as e:
            self.log(f"Error: {str(e)}", "✖")
            messagebox.showerror("Error", str(e))
            self.btn_stop.pack_forget()
            self.btn_dashboard.pack_forget()
            self.btn_internal_dashboard.pack_forget()
            self.btn_start.pack(side="left", padx=4)

        finally:
            config.gui_running = False
            if self.btn_start.winfo_exists():
                self.btn_start.config(state="normal")

    def stop_action(self) -> None:
        self.log("Cerrando conexión...", "→")
        cleanup()
        config.gui_running = False

        self.btn_stop.pack_forget()
        self.btn_dashboard.pack_forget()
        self.btn_internal_dashboard.pack_forget()
        self.btn_start.pack(side="left", padx=4)
        self.btn_start.config(state="normal")

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

        self.log("Desconectado. Puedes iniciar de nuevo.", "✓")
        self.update_idletasks()

    def open_external_dashboard(self) -> None:
        url = _local_url()
        self.log("Abriendo en tu navegador...", "→")
        webbrowser.open(url, new=2)

    def open_internal_dashboard(self) -> None:
        url = _local_url()
        self.log("Abriendo ventana...", "→")
        try:
            ok, err = open_webview_browser(url)
            if ok:
                self.log("Ventana lista", "✓")
                return

            ok, err = open_qt_browser(url)
            if ok:
                self.log("Ventana lista", "✓")
                return

            browser = SimpleBrowser(self, url)
            browser.deiconify()
            browser.lift()
            browser.focus_force()
            self.log("Ventana lista", "✓")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir la ventana:\n{exc}")

    def on_closing(self) -> None:
        if messagebox.askokcancel("Salir", "¿Cerrar NetSphere?"):
            cleanup()
            self.destroy()


def run_gui() -> None:
    app = NetSphereApp()
    app.mainloop()
