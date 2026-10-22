import os
import subprocess
import sys

from flask import Flask, jsonify, request

app = Flask(__name__)
CLAVE = os.environ.get("PPT_API_KEY", "cambia-esta-clave")
CARPETA = os.path.dirname(os.path.abspath(__file__))

CAMPOS = {
    "ganancia": int,
    "perdida": int,
    "preciobs": int,
    "precioq": int,
    "aumentomult": float,
    "basepot": float,
}


@app.post("/ppt")
def lanzar():
    if request.headers.get("X-API-Key") != CLAVE:
        return jsonify(error="No autorizado"), 401

    datos = request.get_json(silent=True) or request.args
    try:
        params = {c: tipo(datos[c]) for c, tipo in CAMPOS.items()}
    except KeyError as e:
        return jsonify(error=f"Falta el parametro {e.args[0]}"), 400
    except (ValueError, TypeError):
        return jsonify(error="Parametros no validos"), 400

    # El juego se abre en un proceso aparte, porque tkinter bloquea con mainloop()
    subprocess.Popen(
        [sys.executable, os.path.join(CARPETA, "lanzar_ppt.py")]
        + [str(params[c]) for c in CAMPOS],
        cwd=CARPETA,
    )
    return jsonify(estado="lanzado", parametros=params), 202


@app.get("/salud")
def salud():
    return jsonify(estado="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
