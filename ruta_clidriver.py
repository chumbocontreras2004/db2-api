"""Imprime la ruta de la carpeta clidriver (driver de DB2) del entorno actual."""
import os
import site
import sys

sys.stdout.reconfigure(encoding="utf-8")
for carpeta in site.getsitepackages():
    ruta = os.path.join(carpeta, "clidriver")
    if os.path.isdir(ruta):
        print(ruta)
        break
