"""Lanzador de Piedra, Papel o Tijeras.

- Pide la contrasena de z/OSMF al arrancar (no se guarda en ningun sitio).
- Al pulsar una dificultad, envia al mainframe el JCL asociado.
- Ese JCL escribe la peticion en USS; el vigilante integrado la lee y abre el juego.
"""

import base64
import json
import multiprocessing
import queue
import ssl
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import simpledialog
import os
import sys


def _preparar_clidriver():
    """En el .exe, indica a Windows donde estan las DLL del driver de DB2 (ibm_db)."""
    base = getattr(sys, "_MEIPASS", None)  # carpeta temporal del .exe
    if not base:
        return
    raiz = os.path.join(base, "clidriver")
    for carpeta, _, archivos in os.walk(raiz):
        if any(a.lower().endswith(".dll") for a in archivos):
            os.add_dll_directory(carpeta)
            os.environ["PATH"] = carpeta + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("IBM_DB_HOME", raiz)


_preparar_clidriver()  # debe ejecutarse antes de que nadie importe ibm_db


def _redirigir_salida():
    """Sin consola (--noconsole) no hay donde imprimir: se guarda en JuegoPPT.log."""
    if getattr(sys, "frozen", False) and sys.stdout is None:
        try:
            ruta = os.path.join(os.path.dirname(sys.executable), "JuegoPPT.log")
            sys.stdout = sys.stderr = open(ruta, "a", encoding="utf-8", buffering=1)
        except OSError:
            pass


_redirigir_salida()

# ======================= CONFIGURACION (edita esto) =======================
ZOSMF = "https://10.1.14.102:10443"  # cambia PUERTO por el tuyo
USUARIO = "TSOPSSB"
CLAVE = "Adrian17"  # si la rellenas, no se pedira al abrir
CERT_INSEGURO = True  # True si el certificado es autofirmado
RUTA_PETICION = "/u/pss/students/tsopssb/peticion_ppt.txt"
INTERVALO = 5  # segundos entre consultas

# (texto del boton, miembro JCL en el mainframe, color)
DIFICULTADES = [
    ("Fácil", "TSOPSSB.PSSOCT26.JCL(PPTFACIL)", "#4caf50"),
    ("Medio", "TSOPSSB.PSSOCT26.JCL(PPTMEDIO)", "#f2b705"),
    ("Difícil", "TSOPSSB.PSSOCT26.JCL(PPTDFCL)", "#e8553d"),
]
# ==========================================================================


def _abrir_juego(g, p, bs, q, am, bp):
    """Se ejecuta en un proceso aparte para que cada juego tenga su ventana."""
    from ppt import ppt

    ppt(int(g), int(p), int(bs), int(q), float(am), float(bp))


class Lanzador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        clave = (
            CLAVE
            or os.environ.get("ZOSMF_PASS")
            or simpledialog.askstring(
                "z/OSMF", f"Contraseña de {USUARIO}:", show="*", parent=self
            )
        )
        if not clave:
            self.destroy()
            raise SystemExit

        self.title("Piedra, Papel o Tijeras")
        self.geometry("420x460")
        self.resizable(False, False)
        self.configure(bg="#f4f1ea")

        token = base64.b64encode(f"{USUARIO}:{clave}".encode()).decode()
        self.cabeceras = {
            "Authorization": "Basic " + token,
            "X-CSRF-ZOSMF-HEADER": "true",
        }
        self.ctx = ssl.create_default_context()
        if CERT_INSEGURO:
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE

        self.cola = queue.Queue()
        self.parar = threading.Event()
        self._construir()
        self.deiconify()

        threading.Thread(target=self._vigilar, daemon=True).start()
        self.after(200, self._vaciar_cola)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ---------------- INTERFAZ ----------------
    def _construir(self):
        tk.Label(
            self,
            text="✊✋✌️ Piedra, Papel o Tijeras",
            font=("Arial", 16, "bold"),
            bg="#f4f1ea",
        ).pack(pady=(16, 4))
        tk.Label(
            self,
            text="Elige la dificultad",
            font=("Arial", 11),
            fg="#777",
            bg="#f4f1ea",
        ).pack(pady=(0, 10))

        for nombre, miembro, color in DIFICULTADES:
            tk.Button(
                self,
                text=nombre,
                font=("Arial", 14, "bold"),
                bg=color,
                fg="#222",
                activebackground=color,
                relief="flat",
                pady=8,
                command=lambda n=nombre, m=miembro: self._enviar(n, m),
            ).pack(fill="x", padx=40, pady=5)

        tk.Label(
            self, text="Estado", font=("Arial", 10, "bold"), fg="#777", bg="#f4f1ea"
        ).pack(anchor="w", padx=16, pady=(14, 2))
        self.txt = tk.Text(
            self,
            height=9,
            font=("Consolas", 9),
            bg="white",
            state="disabled",
            wrap="word",
        )
        self.txt.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _log(self, mensaje):
        self.cola.put(mensaje)

    def _vaciar_cola(self):
        while not self.cola.empty():
            mensaje = self.cola.get()
            self.txt.config(state="normal")
            self.txt.insert("end", time.strftime("%H:%M:%S ") + mensaje + "\n")
            self.txt.see("end")
            self.txt.config(state="disabled")
        self.after(200, self._vaciar_cola)

    def _cerrar(self):
        self.parar.set()
        self.destroy()

    # ---------------- z/OSMF ----------------
    def _llamar(self, url, metodo="GET", cuerpo=None, extra=None):
        cab = dict(self.cabeceras)
        if extra:
            cab.update(extra)
        req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cab)
        return urllib.request.urlopen(req, timeout=15, context=self.ctx)

    def _enviar(self, nombre, miembro):
        self._log(f"Enviando JCL de dificultad {nombre} ({miembro})...")

        def tarea():
            try:
                cuerpo = json.dumps({"file": f"//'{miembro}'"}).encode()
                r = self._llamar(
                    f"{ZOSMF}/zosmf/restjobs/jobs",
                    "PUT",
                    cuerpo,
                    {"Content-Type": "application/json"},
                )
                datos = json.loads(r.read())
                self._log(f"Job enviado: {datos.get('jobname')} ({datos.get('jobid')})")
            except urllib.error.HTTPError as e:
                detalle = e.read().decode("utf-8", "replace")[:200]
                self._log(f"Error HTTP {e.code} al enviar el JCL: {detalle}")
            except Exception as e:
                self._log(f"Error: {e}")

        threading.Thread(target=tarea, daemon=True).start()

    # ---------------- VIGILANTE ----------------
    def _vigilar(self):
        url = f"{ZOSMF}/zosmf/restfiles/fs{RUTA_PETICION}"
        self._log("Vigilando las peticiones del mainframe...")
        ultimo_error = None
        while not self.parar.is_set():
            texto = ""
            try:
                r = self._llamar(url, extra={"X-IBM-Data-Type": "text"})
                texto = r.read().decode("utf-8", "replace").strip()
                ultimo_error = None
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    self._log(
                        "Usuario o contraseña incorrectos. Cierra y vuelve a abrir."
                    )
                    return
                if (
                    e.code != 404 and ultimo_error != e.code
                ):  # 404 = aun no hay peticion
                    self._log(f"Error HTTP {e.code} al leer la peticion")
                    ultimo_error = e.code
            except Exception as e:
                if ultimo_error != str(e):
                    self._log(f"Error de conexion: {e}")
                    ultimo_error = str(e)

            if texto:
                try:
                    self._llamar(url, "DELETE")  # evita repetirla
                except Exception:
                    pass
                valores = texto.split()
                if len(valores) == 6:
                    self._log(
                        "Peticion recibida: " + " ".join(valores) + " -> abriendo juego"
                    )
                    multiprocessing.Process(
                        target=_abrir_juego, args=valores, daemon=True
                    ).start()
                else:
                    self._log(f"Peticion no valida: {texto}")
            self.parar.wait(INTERVALO)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # imprescindible para el .exe en Windows
    Lanzador().mainloop()
