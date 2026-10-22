@echo off
chcp 65001 >nul
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo No se encuentra uv. Abre este archivo desde una terminal donde uv funcione.
    goto error
)

echo [1/4] Anadiendo PyInstaller al proyecto...
uv add --dev pyinstaller
if errorlevel 1 goto error

echo [2/4] Comprobando que ibm_db esta disponible...
uv run python -c "import ibm_db"
if errorlevel 1 (
    echo Falta ibm_db en el entorno. Ejecuta: uv add ibm_db
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

echo [4/4] Creando el ejecutable, puede tardar un par de minutos...
uv run pyinstaller --noconfirm --onefile --noconsole --name JuegoPPT --hidden-import ppt --hidden-import db2s2 --hidden-import juego --collect-all ibm_db --add-data "%CLID%;clidriver" lanzador_ppt.py
if errorlevel 1 goto error

echo.
echo Listo. El ejecutable esta en: %~dp0dist\JuegoPPT.exe
pause
exit /b 0

:error
echo.
echo Ha fallado algun paso. Lee los mensajes de arriba.
pause
exit /b 1
