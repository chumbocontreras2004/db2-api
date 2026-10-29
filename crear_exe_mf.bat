@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Carpetas propias de esta version (no tocan "build" ni "dist" del otro ejecutable)
set NOMBRE=JuegoPPT_MF
set CARPETA_BUILD=build_mf
set CARPETA_DIST=dist_mf

where uv >nul 2>&1
if errorlevel 1 (
    echo No se encuentra uv. Abre este archivo desde una terminal donde uv funcione.
    goto error
)

echo [0/4] Limpiando compilaciones anteriores de la version MF...
if exist "%CARPETA_DIST%" rd /s /q "%CARPETA_DIST%"
if exist "%CARPETA_BUILD%" rd /s /q "%CARPETA_BUILD%"
if exist "%NOMBRE%.spec" del /f /q "%NOMBRE%.spec"

echo [1/4] Anadiendo dependencias necesarias...
uv add --dev pyinstaller
if errorlevel 1 goto error

uv add python-dotenv pywebview
if errorlevel 1 goto error

echo [2/4] Comprobando librerias en el entorno...
uv run python -c "import ibm_db, webview, dotenv"
if errorlevel 1 (
    echo Faltan librerias en el entorno. Revisa la salida de error anterior.
    goto error
)

echo [3/4] Localizando el driver de DB2 clidriver...
set CLID=
for /f "delims=" %%i in ('uv run python ruta_clidriver.py') do set CLID=%%i
if "%CLID%"=="" (
    echo No se encuentra la carpeta clidriver en el entorno.
    goto error
)
echo Driver encontrado en: %CLID%

if not exist "index_mf.html" (
    echo ERROR: Falta el archivo index_mf.html en la carpeta raiz.
    goto error
)
if not exist "lanzador_ppt_mf.py" (
    echo ERROR: Falta el archivo lanzador_ppt_mf.py en la carpeta raiz.
    goto error
)

echo [4/4] Creando el ejecutable...
uv run pyinstaller --noconfirm --onefile --noconsole --name %NOMBRE% ^
    --distpath "%CARPETA_DIST%" ^
    --workpath "%CARPETA_BUILD%" ^
    --specpath "." ^
    --hidden-import ppt ^
    --hidden-import db2s2 ^
    --hidden-import juego ^
    --hidden-import dotenv ^
    --hidden-import webview.platforms.winforms ^
    --collect-all ibm_db ^
    --collect-all webview ^
    --add-data "index_mf.html;." ^
    --add-data "%CLID%;clidriver" ^
    lanzador_ppt_mf.py
if errorlevel 1 goto error

echo.
echo Listo. El ejecutable esta en: %~dp0%CARPETA_DIST%\%NOMBRE%.exe
echo Recuerda que si usas un archivo .env para las credenciales, debe estar junto a %NOMBRE%.exe en la carpeta %CARPETA_DIST%.
pause
exit /b 0

:error
echo.
echo Ha fallado algun paso. Lee los mensajes de arriba.
pause
exit /b 1
