@echo off
setlocal EnableExtensions
title RPF - Registro de Personas
rem ==========================================================================
rem  Sistema Local de Registro de Personas
rem  1. Prepara el PC (solo instala lo que falte):
rem       Node.js, Python, Tesseract OCR + idioma espanol, entorno virtual,
rem       paquetes de Python (requirements.txt), paquetes del front (npm),
rem       base de datos (migrate).
rem  2. Inicia la API (Django) y el front (React/Vite) en segundo plano.
rem  3. Abre la aplicacion; al cerrar su ventana se detiene todo.
rem
rem  Ubicacion: en la carpeta del proyecto Django (junto a manage.py).
rem  Registros: logs\api.log, logs\front.log
rem  Forzar reinstalacion de paquetes:  iniciar.cmd reinstalar
rem ==========================================================================

rem ---------------- Configuracion -------------------------------------------
set "API_PORT=8000"
set "FRONT_PORT=5173"
rem 1 = ventana tipo aplicacion (Edge/Chrome); al cerrarla se detiene todo.
rem 0 = pestana normal del navegador; se detiene con una tecla en esta ventana.
set "MODO_APP=1"
rem Paquetes de winget (se instalan solo si faltan)
set "WINGET_PYTHON=Python.Python.3.13"
set "WINGET_NODE=OpenJS.NodeJS.LTS"
set "WINGET_TESSERACT=UB-Mannheim.TesseractOCR"
set "SPA_URL=https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata"
rem Paquetes que el sistema necesita aunque no esten en requirements.txt
set "PIP_EXTRA=pytesseract opencv-python-headless numpy openpyxl"
set "PIP_TODO=django djangorestframework django-cors-headers drf-spectacular django-silk djangorestframework-simplejwt pillow %PIP_EXTRA%"
set "PY_IMPORTS=import django, rest_framework, corsheaders, drf_spectacular, silk, rest_framework_simplejwt, PIL, pytesseract, cv2, numpy, openpyxl"
rem --------------------------------------------------------------------------

set "BACKEND_DIR=%~dp0"
if "%BACKEND_DIR:~-1%"=="\" set "BACKEND_DIR=%BACKEND_DIR:~0,-1%"
set "API_URL=http://127.0.0.1:%API_PORT%/api/v1/signup/list/"
set "FRONT_URL=http://localhost:%FRONT_PORT%"
set "PF86=%ProgramFiles(x86)%"
set "LOG_DIR=%BACKEND_DIR%\logs"
set "REINSTALAR="
if /i "%~1"=="reinstalar" set "REINSTALAR=1"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%BACKEND_DIR%\manage.py" (
    echo [ERROR] No se encontro manage.py en "%BACKEND_DIR%".
    echo         Copia este archivo en la carpeta del proyecto Django.
    goto fallo
)

set "FRONT_DIR="
for %%D in ("%BACKEND_DIR%\rpf_front" "%BACKEND_DIR%\..\rpf_front") do (
    if not defined FRONT_DIR if exist "%%~D\package.json" set "FRONT_DIR=%%~fD"
)
if not defined FRONT_DIR (
    echo [ERROR] No se encontro la carpeta rpf_front con package.json.
    goto fallo
)

echo ==========================================================
echo  Preparando el sistema ^(la primera vez puede tardar varios
echo  minutos; Windows puede pedir permisos de administrador^)
echo ==========================================================
echo.
call :preparar_node        || goto fallo
call :preparar_python      || goto fallo
call :dependencias_python  || goto fallo
call :preparar_tesseract
call :dependencias_front   || goto fallo
call :base_de_datos        || goto fallo
echo.
echo [OK] Sistema preparado.
echo.
goto iniciar_servidores


rem ==========================================================================
rem  PREPARACION
rem ==========================================================================

:preparar_node
echo [1/6] Node.js
where npm >nul 2>nul
if not errorlevel 1 (
    echo       ya instalado.
    exit /b 0
)
call :winget_instalar "%WINGET_NODE%" "Node.js LTS" || exit /b 1
if exist "%ProgramFiles%\nodejs\npm.cmd" set "PATH=%ProgramFiles%\nodejs;%PATH%"
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js no quedo disponible. Cierra esta ventana y vuelve a ejecutar iniciar.cmd.
    exit /b 1
)
exit /b 0


:preparar_python
echo [2/6] Python y entorno virtual
set "VENV_DIR="
for %%V in ("%BACKEND_DIR%\venv" "%BACKEND_DIR%\.venv" "%BACKEND_DIR%\env" "%BACKEND_DIR%\..\venv" "%BACKEND_DIR%\..\.venv") do (
    if not defined VENV_DIR if exist "%%~V\Scripts\python.exe" set "VENV_DIR=%%~fV"
)
if defined VENV_DIR (
    "%VENV_DIR%\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 goto venv_listo
    echo       El entorno virtual "%VENV_DIR%" esta danado; se creara uno nuevo.
    rmdir /s /q "%VENV_DIR%"
)
set "VENV_DIR=%BACKEND_DIR%\venv"

call :buscar_python
if not defined BASE_PY (
    call :winget_instalar "%WINGET_PYTHON%" "Python 3.13" "--scope user" || exit /b 1
    call :buscar_python
)
if not defined BASE_PY (
    echo [ERROR] No se encontro Python 3.12 o superior.
    echo         Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH".
    exit /b 1
)
echo       Creando entorno virtual en "%VENV_DIR%" ...
%BASE_PY% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    exit /b 1
)
set "REINSTALAR=1"

:venv_listo
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
echo       %VENV_DIR%
exit /b 0


:buscar_python
rem Deja en BASE_PY un Python 3.12+ (el lanzador "py", "python" o una ruta conocida)
set "BASE_PY="
for %%C in ("py -3.13" "py -3.12" "py -3" "python") do (
    if not defined BASE_PY (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1 && set "BASE_PY=%%~C"
    )
)
for %%D in ("%LocalAppData%\Programs\Python\Python313" "%LocalAppData%\Programs\Python\Python312" "%ProgramFiles%\Python313" "%ProgramFiles%\Python312") do (
    if not defined BASE_PY if exist "%%~D\python.exe" set "BASE_PY="%%~D\python.exe""
)
exit /b 0


:dependencias_python
echo [3/6] Paquetes de Python
set "REQ=%BACKEND_DIR%\requirements.txt"
set "MARCA=%VENV_DIR%\.rpf_paquetes"
set "HUELLA=sin-requirements %PIP_EXTRA%"
if exist "%REQ%" (
    for /f "delims=" %%H in ('certutil -hashfile "%REQ%" SHA256 ^| findstr /v ":"') do set "HUELLA=%%H %PIP_EXTRA%"
)
set "HUELLA_ANT="
if exist "%MARCA%" set /p HUELLA_ANT=<"%MARCA%"

if not defined REINSTALAR if "%HUELLA%"=="%HUELLA_ANT%" (
    "%PYTHON%" -c "%PY_IMPORTS%" >nul 2>&1
    if not errorlevel 1 (
        echo       ya instalados.
        exit /b 0
    )
)

echo       Instalando (requiere internet)...
"%PYTHON%" -m pip install --upgrade pip --disable-pip-version-check -q
if exist "%REQ%" (
    "%PYTHON%" -m pip install -r "%REQ%" --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de requirements.txt. Revisa el mensaje de arriba.
        exit /b 1
    )
) else (
    echo       No hay requirements.txt; se instalan los paquetes basicos.
    "%PYTHON%" -m pip install %PIP_TODO% --disable-pip-version-check
)

"%PYTHON%" -c "%PY_IMPORTS%" >nul 2>&1
if errorlevel 1 (
    echo       Agregando paquetes que faltan en requirements.txt: %PIP_EXTRA%
    "%PYTHON%" -m pip install %PIP_EXTRA% --disable-pip-version-check
)
"%PYTHON%" -c "%PY_IMPORTS%"
if errorlevel 1 (
    echo [ERROR] Faltan paquetes de Python ^(ver el modulo indicado arriba^).
    exit /b 1
)
> "%MARCA%" echo %HUELLA%
echo       listo.
exit /b 0


:preparar_tesseract
rem No es fatal: sin Tesseract la app funciona, pero no escanea carnets.
echo [4/6] Tesseract OCR
call :buscar_tesseract
if not defined TESS_EXE (
    call :winget_instalar "%WINGET_TESSERACT%" "Tesseract OCR"
    call :buscar_tesseract
)
if not defined TESS_EXE (
    echo [AVISO] Tesseract no esta instalado: el escaneo de carnets no funcionara.
    echo         Descargalo de https://github.com/UB-Mannheim/tesseract/wiki
    exit /b 0
)
set "TESSERACT_CMD=%TESS_EXE%"
for %%T in ("%TESS_EXE%") do set "TESSDATA=%%~dpTtessdata"
echo       %TESS_EXE%

if exist "%TESSDATA%\spa.traineddata" exit /b 0
echo       Descargando idioma espanol (tildes y N)...
curl -L --fail -s -o "%TEMP%\spa.traineddata" "%SPA_URL%"
if errorlevel 1 (
    echo [AVISO] No se pudo descargar el idioma espanol; se leera sin tildes.
    exit /b 0
)
copy /y "%TEMP%\spa.traineddata" "%TESSDATA%\" >nul 2>&1
if not exist "%TESSDATA%\spa.traineddata" (
    echo       Se necesitan permisos de administrador para copiarlo...
    powershell -NoProfile -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile','-Command','Copy-Item -LiteralPath ''%TEMP%\spa.traineddata'' -Destination ''%TESSDATA%'' -Force'"
)
if exist "%TESSDATA%\spa.traineddata" (
    echo       idioma espanol instalado.
) else (
    echo [AVISO] No se pudo instalar el idioma espanol; se leera sin tildes.
)
exit /b 0


:buscar_tesseract
set "TESS_EXE="
for %%T in ("%ProgramFiles%\Tesseract-OCR\tesseract.exe" "%PF86%\Tesseract-OCR\tesseract.exe" "%LocalAppData%\Programs\Tesseract-OCR\tesseract.exe" "%LocalAppData%\Tesseract-OCR\tesseract.exe") do (
    if not defined TESS_EXE if exist "%%~T" set "TESS_EXE=%%~T"
)
if not defined TESS_EXE (
    for /f "delims=" %%T in ('where tesseract 2^>nul') do if not defined TESS_EXE set "TESS_EXE=%%T"
)
exit /b 0


:dependencias_front
echo [5/6] Paquetes del front (npm)
if not exist "%FRONT_DIR%\.env" (
    > "%FRONT_DIR%\.env" echo VITE_API_URL=http://127.0.0.1:%API_PORT%/api/v1
    echo       Creado rpf_front\.env
)
set "LOCK=%FRONT_DIR%\package-lock.json"
if not exist "%LOCK%" set "LOCK=%FRONT_DIR%\package.json"
set "MARCA_NPM=%FRONT_DIR%\node_modules\.rpf_paquetes"
set "HUELLA_NPM="
for /f "delims=" %%H in ('certutil -hashfile "%LOCK%" SHA256 ^| findstr /v ":"') do set "HUELLA_NPM=%%H"
set "HUELLA_NPM_ANT="
if exist "%MARCA_NPM%" set /p HUELLA_NPM_ANT=<"%MARCA_NPM%"

if not defined REINSTALAR if exist "%FRONT_DIR%\node_modules\.bin\vite.cmd" if "%HUELLA_NPM%"=="%HUELLA_NPM_ANT%" (
    echo       ya instalados.
    exit /b 0
)
echo       Instalando (requiere internet)...
pushd "%FRONT_DIR%"
call npm install --no-fund --no-audit
set "NPM_ERR=%ERRORLEVEL%"
popd
if not "%NPM_ERR%"=="0" (
    echo [ERROR] Fallo npm install. Revisa el mensaje de arriba.
    exit /b 1
)
rem npm install pudo crear package-lock.json: la huella se toma de ese archivo
if exist "%FRONT_DIR%\package-lock.json" set "LOCK=%FRONT_DIR%\package-lock.json"
for /f "delims=" %%H in ('certutil -hashfile "%LOCK%" SHA256 ^| findstr /v ":"') do set "HUELLA_NPM=%%H"
> "%MARCA_NPM%" echo %HUELLA_NPM%
echo       listo.
exit /b 0


:base_de_datos
echo [6/6] Base de datos
pushd "%BACKEND_DIR%"
"%PYTHON%" manage.py migrate --noinput -v 0
set "MIG_ERR=%ERRORLEVEL%"
popd
if not "%MIG_ERR%"=="0" (
    echo [ERROR] Fallo "manage.py migrate". Revisa el mensaje de arriba.
    exit /b 1
)
echo       al dia.
exit /b 0


:winget_instalar
rem  %1 = id de winget, %2 = nombre visible, %3 = opciones extra (opcional)
where winget >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Falta %~2 y no esta disponible "winget" para instalarlo.
    echo         Instala "Instalador de aplicacion" desde Microsoft Store,
    echo         o instala %~2 manualmente y vuelve a ejecutar iniciar.cmd.
    exit /b 1
)
echo       Instalando %~2 con winget...
winget install -e --id %~1 %~3 --accept-package-agreements --accept-source-agreements --silent
call :refrescar_path
exit /b 0


:refrescar_path
rem Lee el PATH actualizado del registro (lo que acaba de agregar un instalador)
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P"
exit /b 0


rem ==========================================================================
rem  INICIO DE LOS SERVIDORES
rem ==========================================================================

:iniciar_servidores
set "PYTHONUNBUFFERED=1"

curl -s -o nul "%API_URL%" 2>nul
if errorlevel 1 (
    echo Iniciando API en http://127.0.0.1:%API_PORT% ...
    start "" /B /D "%BACKEND_DIR%" cmd /c ""%PYTHON%" manage.py runserver 127.0.0.1:%API_PORT% --noreload > "%LOG_DIR%\api.log" 2>&1"
) else (
    echo La API ya estaba en ejecucion.
)

curl -s -o nul "%FRONT_URL%" 2>nul
if errorlevel 1 (
    echo Iniciando front en %FRONT_URL% ...
    start "" /B /D "%FRONT_DIR%" cmd /c "npm run dev -- --port %FRONT_PORT% --strictPort > "%LOG_DIR%\front.log" 2>&1"
) else (
    echo El front ya estaba en ejecucion.
)

echo Esperando a que los servidores esten listos...
set /a INTENTOS=0
:esperar
curl -s -o nul "%API_URL%" 2>nul
if errorlevel 1 goto no_listo
curl -s -o nul "%FRONT_URL%" 2>nul
if errorlevel 1 goto no_listo
goto abrir

:no_listo
set /a INTENTOS+=1
if %INTENTOS% geq 60 goto fallo_inicio
ping -n 2 127.0.0.1 >nul
goto esperar

:fallo_inicio
echo.
echo [ERROR] Los servidores no respondieron en 60 segundos.
echo ---------------- logs\api.log ----------------
if exist "%LOG_DIR%\api.log" type "%LOG_DIR%\api.log"
echo ---------------- logs\front.log --------------
if exist "%LOG_DIR%\front.log" type "%LOG_DIR%\front.log"
echo ----------------------------------------------
call :detener
goto fallo


rem ==========================================================================
rem  APLICACION
rem ==========================================================================

:abrir
set "NAVEGADOR="
if "%MODO_APP%"=="1" (
    for %%B in (
        "%PF86%\Microsoft\Edge\Application\msedge.exe"
        "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        "%PF86%\Google\Chrome\Application\chrome.exe"
        "%LocalAppData%\Google\Chrome\Application\chrome.exe"
    ) do (
        if not defined NAVEGADOR if exist "%%~B" set "NAVEGADOR=%%~B"
    )
)
if not defined NAVEGADOR goto sin_ventana_app

rem Perfil de navegador exclusivo: permite saber cuando se cierra la ventana
rem de la app sin confundirla con otras ventanas de Edge/Chrome.
set "PERFIL=%LocalAppData%\RPF-navegador-app"
start "" "%NAVEGADOR%" --app=%FRONT_URL% --user-data-dir="%PERFIL%" --no-first-run --no-default-browser-check --window-size=1300,900

echo.
echo Aplicacion abierta. Al cerrar su ventana se detendran la API y el front.
echo (Si cierras ESTA ventana tambien se detiene todo.)
ping -n 6 127.0.0.1 >nul

:esperar_cierre
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'msedge.exe' -or $_.Name -eq 'chrome.exe') -and $_.CommandLine -like '*RPF-navegador-app*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 goto app_cerrada
ping -n 3 127.0.0.1 >nul
goto esperar_cierre

:sin_ventana_app
start "" "%FRONT_URL%"
echo.
echo Aplicacion abierta en el navegador.
echo Presiona una tecla en ESTA ventana para detener la API y el front...
pause >nul

:app_cerrada
call :detener
exit /b 0


:detener
echo Deteniendo la API y el front...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'python*' -and $_.CommandLine -like '*manage.py*runserver*:%API_PORT%*') -or ($_.Name -eq 'node.exe' -and $_.CommandLine -like '*vite*--port*%FRONT_PORT%*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%API_PORT% .*LISTENING" /C:":%API_PORT% .*ESCUCHANDO" /C:":%FRONT_PORT% .*LISTENING" /C:":%FRONT_PORT% .*ESCUCHANDO"') do (
    taskkill /PID %%P /T /F >nul 2>&1
)
echo Listo.
exit /b 0


:fallo
echo.
echo No se pudo iniciar el sistema. Revisa el mensaje de arriba.
pause
exit /b 1
