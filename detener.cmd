@echo off
rem Detiene manualmente la API y el front iniciados con iniciar.cmd
set "API_PORT=8000"
set "FRONT_PORT=5173"

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'python*' -and $_.CommandLine -like '*manage.py*runserver*:%API_PORT%*') -or ($_.Name -eq 'node.exe' -and $_.CommandLine -like '*vite*--port*%FRONT_PORT%*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%API_PORT% .*LISTENING" /C:":%API_PORT% .*ESCUCHANDO" /C:":%FRONT_PORT% .*LISTENING" /C:":%FRONT_PORT% .*ESCUCHANDO"') do (
    taskkill /PID %%P /T /F >nul 2>&1
)
echo Servidores detenidos.
ping -n 3 127.0.0.1 >nul
