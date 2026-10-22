"""Lanzador y Core de Piedra, Papel o Tijera en HTML nativo a pantalla completa.

- Se conecta a z/OSMF.
- Envía el JCL al pulsar la dificultad en el HTML.
- El vigilante lee el archivo en USS y abre la vista del juego en la misma ventana.
"""

import base64
import inspect
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webview

T0 = time.time()  # referencia para los mensajes [diag]


def _t():
    return f"{time.time() - T0:.1f}s"


def _preparar_clidriver():
    """En el .exe, indica a Windows donde estan las DLL del driver de DB2 (ibm_db)."""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return
    raiz = os.path.join(base, "clidriver")
    for carpeta, _, archivos in os.walk(raiz):
        if any(a.lower().endswith(".dll") for a in archivos):
            os.add_dll_directory(carpeta)
            os.environ["PATH"] = carpeta + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("IBM_DB_HOME", raiz)


_preparar_clidriver()


def _redirigir_salida():
    if getattr(sys, "frozen", False) and sys.stdout is None:
        try:
            ruta = os.path.join(os.path.dirname(sys.executable), "JuegoPPT.log")
            sys.stdout = sys.stderr = open(ruta, "a", encoding="utf-8", buffering=1)
        except OSError:
            pass


_redirigir_salida()


def _ruta_recurso(nombre):
    """Encuentra index.html tanto en desarrollo como dentro del .exe de PyInstaller."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, nombre)


import os
import sys
from dotenv import load_dotenv

# Localiza la carpeta real donde está el script o el .exe
if getattr(sys, "frozen", False):
    carpeta_base = os.path.dirname(sys.executable)
else:
    carpeta_base = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(carpeta_base, ".env"))

# ======================= CONFIGURACION REAL =======================
ZOSMF = "https://10.1.14.102:10443"
USUARIO = os.getenv("ZOSMF_USER", "TSOPSSB")
CLAVE = os.getenv("ZOSMF_PASS", "")
CERT_INSEGURO = True
RUTA_PETICION = "/u/pss/students/tsopssb/peticion_ppt.txt"
INTERVALO = 5
# Puerto local donde escucha el guardian externo: el boton Salir del HTML conecta aqui
# para forzar el cierre aunque Python este bloqueado (debe coincidir con index.html).
PUERTO_SALIDA = 48931

DIFICULTADES = {
    "facil": ("Fácil", "TSOPSSB.PSSOCT26.JCL(PPTFACIL)"),
    "medio": ("Medio", "TSOPSSB.PSSOCT26.JCL(PPTMEDIO)"),
    "dificil": ("Difícil", "TSOPSSB.PSSOCT26.JCL(PPTDFCL)"),
}
# ==================================================================


class BridgeApp:
    def __init__(self):
        self.ventana = None
        self.juego_instancia = None
        self.parar = threading.Event()
        self.enviando_job = False
        self._vigilante_iniciado = False
        self.api_lista = threading.Event()  # se activa cuando pywebview ya esta operativo
        self._logs = []
        self._logs_lock = threading.Lock()
        self._lock_vigilante = threading.Lock()

        # Configuración HTTP z/OSMF
        token = base64.b64encode(f"{USUARIO}:{CLAVE}".encode()).decode()
        self.cabeceras = {
            "Authorization": "Basic " + token,
            "X-CSRF-ZOSMF-HEADER": "true",
        }
        self.ctx = ssl.create_default_context()
        if CERT_INSEGURO:
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE

    def iniciar_vigilante(self):
        """Arranca el vigilante una sola vez (lo llame quien lo llame)."""
        with self._lock_vigilante:
            if self._vigilante_iniciado:
                return
            self._vigilante_iniciado = True
        threading.Thread(target=self._vigilar, daemon=True).start()

    def listo(self):
        """La llama el HTML en cuanto pywebview esta listo: arranque inmediato, sin esperas."""
        self.api_lista.set()
        self.log(f"[diag] API de pywebview lista a los {_t()} del arranque de Python")
        self.iniciar_vigilante()

    def set_ventana(self, ventana):
        self.ventana = ventana
        self.iniciar_vigilante()

    # ---------------- z/OSMF ----------------
    def _llamar(self, url, metodo="GET", cuerpo=None, extra=None):
        cab = dict(self.cabeceras)
        if extra:
            cab.update(extra)
        req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cab)
        return urllib.request.urlopen(req, timeout=15, context=self.ctx)

    def enviar_dificultad(self, clave_dif):
        """Llamado desde los botones del HTML con bloqueo anti-spam."""
        if self.enviando_job:
            self.log("Ya hay un job en proceso de envío. Espera a que termine.")
            return

        if clave_dif not in DIFICULTADES:
            return

        self.enviando_job = True
        nombre, miembro = DIFICULTADES[clave_dif]

        def tarea():
            self.log(f"Enviando JCL de dificultad {nombre} ({miembro})...")
            try:
                cuerpo = json.dumps({"file": f"//'{miembro}'"}).encode()
                r = self._llamar(
                    f"{ZOSMF}/zosmf/restjobs/jobs",
                    "PUT",
                    cuerpo,
                    {"Content-Type": "application/json"},
                )
                datos = json.loads(r.read())
                self.log(f"Job enviado: {datos.get('jobname')} ({datos.get('jobid')})")
                threading.Thread(
                    target=self._seguir_job,
                    args=(datos.get("jobname"), datos.get("jobid")),
                    daemon=True,
                ).start()
            except urllib.error.HTTPError as e:
                detalle = e.read().decode("utf-8", "replace")[:200]
                self.log(f"Error HTTP {e.code} al enviar el JCL: {detalle}")
                self._restaurar_botones_html()
            except Exception as e:
                self.log(f"Error: {e}")
                self._restaurar_botones_html()

        threading.Thread(target=tarea, daemon=True).start()

    def _seguir_job(self, jobname, jobid):
        """Muestra en la terminal el estado real del job (INPUT/ACTIVE/OUTPUT y retcode).

        Sirve para ver si un job anterior se quedo abierto o en cola, o si el job
        termino con error y por eso nunca llega la peticion.
        """
        if not jobname or not jobid:
            return
        url = f"{ZOSMF}/zosmf/restjobs/jobs/{jobname}/{jobid}"
        ultimo = None
        errores = 0
        inicio = time.time()
        while not self.parar.is_set() and time.time() - inicio < 180:
            try:
                d = json.loads(self._llamar(url).read())
                errores = 0
                status = d.get("status")
                retcode = d.get("retcode") or ""
                estado = f"{status} {retcode}".strip()
                if estado != ultimo:
                    self.log(f"Job {jobname} ({jobid}): {estado}")
                    ultimo = estado
                if status == "OUTPUT":
                    if not retcode.startswith("CC 0000"):
                        self.log(
                            f"El job termino con {retcode or 'resultado desconocido'}: "
                            "no llegara ninguna peticion. Puedes reintentar."
                        )
                        self._restaurar_botones_html()
                    return
            except Exception as e:
                errores += 1
                if errores == 3:
                    self.log(f"No se puede consultar el estado del job: {e}")
            self.parar.wait(3)
        if not self.parar.is_set():
            self.log(
                f"El job sigue en {ultimo} tras 3 min: puede estar en cola o "
                "bloqueado por otro job anterior. Revisalo en SDSF."
            )
            self._restaurar_botones_html()

    def _restaurar_botones_html(self):
        """Reactiva los botones si hubo un error en la llamada."""
        self.enviando_job = False
        if self.ventana:
            self.ventana.evaluate_js("""
                enviandoActivo = false;
                document.querySelectorAll('.btn-dif').forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                    btn.style.cursor = 'pointer';
                });
                const tFacil = document.querySelector('.btn-dif.facil .btn-dif-text');
                const tMedio = document.querySelector('.btn-dif.medio .btn-dif-text');
                const tDif = document.querySelector('.btn-dif.dificil .btn-dif-text');
                if (tFacil) tFacil.textContent = 'FÁCIL';
                if (tMedio) tMedio.textContent = 'MEDIO';
                if (tDif) tDif.textContent = 'DIFÍCIL';
            """)

    # ---------------- VIGILANTE ----------------
    def _vigilar(self):
        url = f"{ZOSMF}/zosmf/restfiles/fs{RUTA_PETICION}"
        self.log(f"Vigilando las peticiones del mainframe... (a los {_t()})")
        ultimo_error = None
        invalidos = 0

        while not self.parar.is_set():
            texto = ""
            try:
                r = self._llamar(url, extra={"X-IBM-Data-Type": "text"})
                texto = r.read().decode("utf-8", "replace").strip()
                ultimo_error = None
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    self.log("Usuario o contraseña incorrectos.")
                    return
                if e.code != 404 and ultimo_error != e.code:
                    self.log(f"Error HTTP {e.code} al leer la peticion")
                    ultimo_error = e.code
            except Exception as e:
                if ultimo_error != str(e):
                    self.log(f"Error de conexion: {e}")
                    ultimo_error = str(e)

            if texto:
                valores = texto.split()
                if len(valores) == 7:
                    invalidos = 0
                    try:
                        self._llamar(url, "DELETE")
                    except Exception:
                        pass
                    self.log(
                        "Peticion recibida: " + " ".join(valores) + " -> abriendo juego"
                    )
                    try:
                        import ppt

                        self.juego_instancia = ppt.crear_juego(
                            int(valores[0]),
                            int(valores[1]),
                            int(valores[2]),
                            float(valores[3]),
                            int(valores[4]),
                            float(valores[5]),
                            float(valores[6]),
                        )
                        estado = self.juego_instancia.obtener_estado()
                        if self.ventana:
                            self.ventana.evaluate_js(
                                f"iniciarVistaJuego({json.dumps(estado)})"
                            )
                    except Exception as e:
                        # Un fallo aqui ya no mata al vigilante ni deja los botones bloqueados
                        self.log(f"Error al abrir el juego: {e}")
                        self._restaurar_botones_html()
                else:
                    # Puede ser un archivo a medio escribir: no se borra hasta confirmar
                    invalidos += 1
                    if invalidos >= 3:
                        self.log(f"Peticion no valida: {texto}")
                        try:
                            self._llamar(url, "DELETE")
                        except Exception:
                            pass
                        invalidos = 0
                        self._restaurar_botones_html()
            else:
                invalidos = 0

            self.parar.wait(INTERVALO)

    # ---------------- MÉTODOS DEL JUEGO (DELEGADOS A PPT.PY) ----------------
    def jugar(self, eleccion):
        if self.juego_instancia:
            return self.juego_instancia.jugar(eleccion)

    def comprar(self, item):
        if self.juego_instancia:
            return self.juego_instancia.comprar(item)

    def volver_a_dificultad(self):
        """El HTML vuelve a la pantalla de dificultad: se olvida la partida y se libera el envio."""
        if self.juego_instancia is not None:
            # Las monedas vuelven a 0 al salir de la partida (victoria final o reinicio)
            try:
                if hasattr(self.juego_instancia, "monedas"):
                    self.juego_instancia.monedas = 0
            except Exception as e:
                self.log(f"No se pudieron poner las monedas a 0: {e}")
        self.juego_instancia = None
        self.enviando_job = False
        return True

    def reiniciar(self):
        if self.juego_instancia:
            return self.juego_instancia.reiniciar()

    def cerrar(self):
        """Permite que el botón de salir del HTML cierre la ventana inmediatamente."""
        self.parar.set()
        # Si destroy() se bloquea (interfaz congelada), a los 1.5 s se mata el proceso igualmente
        threading.Timer(1.5, lambda: os._exit(0)).start()
        if self.ventana:
            try:
                self.ventana.destroy()
            except Exception:
                pass

    def log(self, mensaje):
        """Guarda la linea en una cola; el HTML la recoge con obtener_logs().

        Asi no se depende de evaluate_js (que espera a la UI y puede tardar)
        y no se pierde nada de lo que se loguee antes de que cargue la pagina.
        """
        linea = f"{time.strftime('%H:%M:%S')} {mensaje}"
        with self._logs_lock:
            self._logs.append(linea)
        try:
            print(linea)
        except Exception:
            pass

    def obtener_logs(self):
        """Lo llama el HTML cada pocos cientos de ms: devuelve y vacia la cola."""
        with self._logs_lock:
            lineas, self._logs = self._logs, []
        if lineas and not getattr(self, "_primera_lectura", False):
            self._primera_lectura = True
            lineas.append(f"[diag] primera lectura de logs a los {_t()}")
        return lineas


def _carpeta_perfil_unica():
    """Carpeta de perfil de WebView2 distinta en cada arranque.

    Si la ejecucion anterior aun tiene vivo su proceso de WebView2, compartir carpeta
    hace que la nueva se quede esperando. Con una carpeta propia no hay conflicto.
    """
    base = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "JuegoPPT_perfiles"
    )
    os.makedirs(base, exist_ok=True)
    for nombre in os.listdir(base):  # limpia restos; los que sigan en uso se ignoran
        shutil.rmtree(os.path.join(base, nombre), ignore_errors=True)
    return tempfile.mkdtemp(prefix="p_", dir=base)


def _vigilar_tecla_salida():
    """Salida de emergencia: mantener Esc 2 s cierra el juego a la fuerza.

    Lee el teclado directamente de Windows, asi que funciona aunque la interfaz
    (WebView2) este congelada y el boton Salir no responda.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        estado_tecla = ctypes.windll.user32.GetAsyncKeyState
    except Exception:
        return
    VK_ESCAPE = 0x1B
    desde = None
    while True:
        if estado_tecla(VK_ESCAPE) & 0x8000:
            if desde is None:
                desde = time.time()
            elif time.time() - desde >= 2:
                try:
                    sys.stdout.flush()
                except Exception:
                    pass
                os._exit(0)
        else:
            desde = None
        time.sleep(0.05)


def _lanzar_guardian_externo():
    """Guardian en un proceso aparte (PowerShell): mantener Esc 2 s, o pulsar Salir, mata el juego.

    Al ser otro proceso, funciona aunque Python entero este bloqueado (por ejemplo una
    llamada a DB2 que no suelta el GIL) o WebView2 congelado, casos en los que un hilo
    dentro del propio juego tampoco podria reaccionar.
    """
    if sys.platform != "win32":
        return
    script = f"""
$sig = '[DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vKey);'
Add-Type -MemberDefinition $sig -Name K -Namespace W
$juego = {os.getpid()}
$desde = $null
$escucha = $null
try {{
    $escucha = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Parse('127.0.0.1'), {PUERTO_SALIDA})
    $escucha.Start()
}} catch {{ $escucha = $null }}
while ($true) {{
    if (-not (Get-Process -Id $juego -ErrorAction SilentlyContinue)) {{ exit }}
    if ($escucha -ne $null -and $escucha.Pending()) {{
        taskkill /PID $juego /T /F | Out-Null
        exit
    }}
    if (([W.K]::GetAsyncKeyState(0x1B) -band 0x8000) -ne 0) {{
        if ($desde -eq $null) {{ $desde = Get-Date }}
        elseif (((Get-Date) - $desde).TotalSeconds -ge 2) {{
            taskkill /PID $juego /T /F | Out-Null
            exit
        }}
    }} else {{ $desde = $null }}
    Start-Sleep -Milliseconds 50
}}
"""
    codificado = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-EncodedCommand",
                codificado,
            ],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _comprobar_guardian(app_instancia):
    """Avisa en la terminal si el guardian externo realmente escucha en su puerto."""
    time.sleep(5)  # PowerShell tarda unos segundos en arrancar y compilar su codigo
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", PUERTO_SALIDA))
        app_instancia.log(
            f"[diag] ⚠ el guardian NO escucha en el puerto {PUERTO_SALIDA}: "
            "el boton Salir solo funcionara por el cierre normal (Esc si sigue valiendo)"
        )
    except OSError:
        app_instancia.log(
            f"[diag] guardian escuchando en el puerto {PUERTO_SALIDA}: Salir forzado listo"
        )
    finally:
        s.close()


def _conexiones_sin_respuesta():
    """Devuelve [(pid, remoto)] de las conexiones TCP en SYN_SENT (intentando conectar, sin respuesta)."""
    salida = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=8,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    ).stdout
    res = []
    for linea in salida.splitlines():
        partes = linea.split()
        # TCP  local:puerto  remoto:puerto  ESTADO  PID
        if len(partes) >= 5 and partes[0].upper() == "TCP" and "SYN" in partes[3].upper():
            res.append((partes[4], partes[2]))
    return res


def _nombre_proceso(pid, cache={}):
    if pid in cache:
        return cache[pid]
    nombre = f"PID {pid}"
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=8,
            creationflags=0x08000000,
        ).stdout.strip()
        if out.startswith('"'):
            nombre = out.split('","')[0].strip('"') + f" (PID {pid})"
    except Exception:
        pass
    cache[pid] = nombre
    return nombre


def _diagnosticar_arranque(app_instancia, limite=40):
    """Mientras WebView2 arranca, anota a que IPs intenta conectar sin recibir respuesta.

    Un retraso de ~21 s exactos es el timeout de conexion TCP de Windows (3+6+12 s): si en
    las ejecuciones lentas aparece aqui una IP en SYN_SENT, esa es la que lo provoca.
    Se detiene en cuanto pywebview esta listo (o a los `limite` segundos).
    """
    if sys.platform != "win32":
        return
    vistas = set()
    avisado_sin_red = False
    while not app_instancia.api_lista.is_set() and time.time() - T0 < limite:
        try:
            for pid, remoto in _conexiones_sin_respuesta():
                if (pid, remoto) not in vistas:
                    vistas.add((pid, remoto))
                    app_instancia.log(
                        f"[diag] a los {_t()}: {_nombre_proceso(pid)} intenta conectar "
                        f"a {remoto} y no recibe respuesta (SYN_SENT)"
                    )
        except Exception as e:
            app_instancia.log(f"[diag] no se pudo ejecutar netstat: {e}")
            return
        if not avisado_sin_red and not vistas and time.time() - T0 > 8:
            avisado_sin_red = True
            app_instancia.log(
                f"[diag] a los {_t()} sigue sin arrancar y NO hay conexiones sin respuesta: "
                "el retraso no parece de red (revisar antivirus, disco o GPU)"
            )
        app_instancia.api_lista.wait(1)


def iniciar_app(app_instancia):
    """Respaldo: si el HTML no avisa con listo() en 5 s, arranca el vigilante igualmente."""
    app_instancia.parar.wait(5)
    app_instancia.iniciar_vigilante()


if __name__ == "__main__":
    app_bridge = BridgeApp()
    ruta_html = _ruta_recurso("index.html")

    ventana = webview.create_window(
        title="Piedra, Papel o Tijera — Mainframe Edition",
        url=ruta_html,
        js_api=app_bridge,
        fullscreen=True,
    )

    app_bridge.ventana = ventana
    app_bridge.log(f"[diag] ventana creada a los {_t()}")
    app_bridge.log("Si se queda congelado: mantén Esc 2 segundos para cerrar el juego.")
    threading.Thread(target=_vigilar_tecla_salida, daemon=True).start()
    if _lanzar_guardian_externo():
        app_bridge.log("[diag] guardian externo de Esc activo (powershell)")
        threading.Thread(
            target=_comprobar_guardian, args=(app_bridge,), daemon=True
        ).start()
    else:
        app_bridge.log("[diag] no se pudo lanzar el guardian externo de Esc")
    # Prueba para el retraso fijo de ~21 s al arrancar WebView2 (parece un timeout):
    # --no-proxy-server evita la autodeteccion de proxy (WPAD) de Edge y
    # --disable-gpu evita la inicializacion de GPU. Se puede sobrescribir desde fuera
    # definiendo la variable de entorno antes de lanzar el .exe.
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--no-proxy-server --disable-gpu"
    )
    app_bridge.log(
        "[diag] WebView2 args: " + os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"]
    )
    threading.Thread(target=_diagnosticar_arranque, args=(app_bridge,), daemon=True).start()
    # Pasamos 'lambda: iniciar_app(app_bridge)' a start para que arranque tras cargar la ventana
    opciones = {"gui": "edgechromium"}
    if "storage_path" in inspect.signature(webview.start).parameters:
        try:
            opciones["storage_path"] = _carpeta_perfil_unica()
        except OSError:
            pass
    webview.start(lambda: iniciar_app(app_bridge), **opciones)

    # Al cerrar la ventana, matar el proceso del todo: si quedara vivo (hilos de DB2, etc.)
    # WebView2 no libera su perfil y la siguiente apertura se queda esperando.
    try:
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(0)
