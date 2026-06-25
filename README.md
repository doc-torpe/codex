# NetSphere

Aplicación multiplataforma para conectarse a equipos de red como
**Ubiquiti**, **TP-Link**, **ZTE** y **Huawei**.

## Origen

El código original se perdió. Este repositorio contiene la recuperación del
código fuente a partir del ejecutable `NetSphere_Bridge.exe` (PyInstaller) más
una refactorización a paquete Python instalable y multiplataforma.

## Características

- Detección automática del equipo objetivo.
- Proxy local en `http://127.0.0.1:6060` por defecto (sin advertencias de
  certificado). Opcionalmente HTTPS con certificado autofirmado.
- Para antenas **Ubiquiti**, abre un túnel SSH hacia el modem detrás de la
  antena (subred `192.168.100.x`) y expone el proxy sobre ese túnel.
- Soporte para TLS legacy en equipos antiguos.
- Interfaz gráfica moderna con tema oscuro (2026 edition).
- **Navegador integrado real** con `pywebview` + `PySide6`: usa el motor web
  nativo del sistema (Edge/WebView2 en Windows, WKWebView en macOS,
  Qt WebEngine/Chromium en Linux).
- Fallback a Qt WebEngine directo y luego a navegador básico tkinter.
- Easter egg: `Alt + 5`.

## Descargar ejecutable (sin instalar Python)

En la sección **Releases** del repositorio encontrarás ejecutables listos para
usar:

| Sistema | Archivo |
|---------|---------|
| Windows | `AirconektaToolFromNetSphere-windows.exe` |
| macOS   | `AirconektaToolFromNetSphere-macos` |
| Linux   | `AirconektaToolFromNetSphere-linux` |

Los builds se generan automáticamente con GitHub Actions cada vez que se publica
un tag `v*`.

## Requisitos

- Python 3.10 o superior.
- tkinter instalado (viene con Python en Windows/macOS; en Linux instala el
  paquete `python3-tk` de tu distribución).
- `pywebview`, `PySide6` y `qtpy` para el navegador integrado real.
- Dependencias listadas en `requirements.txt`.

### Requisitos del sistema para el navegador integrado

El navegador integrado usa `pywebview` con backend Qt/PySide6, que incluye su
propio motor Chromium (Qt WebEngine). No requiere instalar Chrome, Firefox ni
WebKitGTK del sistema.

- **Windows**: WebView2 Runtime (ya viene en Windows 10/11 modernos).
- **macOS**: No requiere nada extra.
- **Linux**: librerías gráficas estándar (X11/Wayland, OpenGL, fontconfig).
  En CachyOS/Arch con un escritorio moderno usualmente ya están.

## Instalación

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Modo GUI
python -m netsphere_bridge --gui

# Modo consola
python -m netsphere_bridge --cli 192.168.1.20
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Modo GUI
python -m netsphere_bridge --gui

# Modo consola
python -m netsphere_bridge --cli 192.168.1.20
```

En distribuciones Linux sin entorno gráfico, usa obligatoriamente `--cli` o
instala tkinter si quieres la GUI:

```bash
# Debian / Ubuntu
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

### Wrapper directo desde el repositorio

También puedes ejecutar el wrapper `app.py` que acepta `-gui` / `-cli`:

```bash
python app.py -gui
python app.py -cli 192.168.1.20
```

### Instalación como paquete editable

```bash
pip install -e .
netsphere-bridge --cli 192.168.1.20
```

## Modo consola (headless)

El modo `--cli` no requiere tkinter. Si no proporcionas la IP, la aplicación la
solicita interactivamente. Para detener el proxy, presiona `Ctrl+C`.

```bash
netsphere-bridge --cli
IP del equipo: 192.168.1.20
```

## Navegador integrado

En la GUI aparecen dos botones de dashboard una vez que el proxy está activo:

- **🌐 Dashboard**: abre `http://127.0.0.1:6060` en el navegador predeterminado
  del sistema con `webbrowser.open()`.
- **🖥️ Integrado**: abre el dashboard dentro de la app usando `pywebview`, que
  renderiza la página con el motor web nativo del sistema (igual que un
  navegador real). No muestra la URL al usuario, solo la interfaz completa.

Si `pywebview` no está disponible, cae automáticamente a un navegador básico
hecho con tkinter.

## Configuración

Las credenciales SSH y los puertos pueden personalizarse mediante variables de
entorno (útil para no hardcodearlas al distribuir la app):

| Variable                  | Valor por defecto   | Descripción |
|---------------------------|---------------------|-------------|
| `NETSPHERE_SSH_USER`      | `airconekta`        | Usuario SSH para antenas |
| `NETSPHERE_SSH_PASS`      | `airconekta.01@`    | Password SSH para antenas |
| `NETSPHERE_LOCAL_PORT`    | `6060`              | Puerto del proxy local |
| `NETSPHERE_TUNNEL_PORT`   | `8443`              | Puerto del túnel SSH local |
| `NETSPHERE_USE_HTTPS`     | `0`                 | `1` para HTTPS local con cert autofirmado |

Ejemplo en Linux/macOS:

```bash
export NETSPHERE_SSH_USER=mi_usuario
export NETSPHERE_SSH_PASS=mi_password
netsphere-bridge
```

## Estructura del proyecto

```
.
├── app.py                     # Wrapper directo: app.py -gui / app.py -cli
├── build.py                   # Script de build con PyInstaller
├── .github/workflows/         # GitHub Actions para builds automáticos
│   └── build.yml
├── src/netsphere_bridge/      # Código fuente del paquete
│   ├── __main__.py            # Punto de entrada con --gui / --cli
│   ├── app.py                 # GUI tkinter
│   ├── browser.py             # Navegador web básico integrado (fallback)
│   ├── cli.py                 # Modo consola headless
│   ├── webview_browser.py     # Navegador integrado real con pywebview
│   ├── cert_manager.py        # Certificados autofirmados
│   ├── config.py              # Constantes y configuración
│   ├── detector.py            # Detección de equipos
│   ├── proxy.py               # Proxy HTTPS con aiohttp
│   ├── ssh_tunnel.py          # Túnel SSH con paramiko
│   └── utils.py               # Utilidades de red
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Compilar ejecutable manualmente

Si prefieres generar tu propio ejecutable, usa PyInstaller:

```bash
pip install -e ".[build]"
python build.py
```

El resultado aparecerá en `dist/`:

- Windows: `dist/AirconektaToolFromNetSphere.exe`
- macOS:   `dist/AirconektaToolFromNetSphere`
- Linux:   `dist/AirconektaToolFromNetSphere`

> Nota: el ejecutable incluye PySide6/QtWebEngine, por lo que pesa
> aproximadamente 250-300 MB.

## Notas de seguridad

- Por defecto el proxy local escucha en HTTP (`127.0.0.1`). El tráfico entre el
  proxy y el equipo remoto sigue cifrado cuando el upstream es HTTPS.
- Si activas `NETSPHERE_USE_HTTPS=1`, se genera un certificado autofirmado en
  tiempo de ejecución.
- Para equipos antiguos se habilitan cifrados y versiones TLS legacy.
- Se recomienda no distribuir credenciales hardcodeadas; usa las variables de
  entorno documentadas arriba.

## Licencia

MIT
