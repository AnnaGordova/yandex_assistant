@echo off
REM Запуск веб-сервера через PowerShell
REM Используется 'py' вместо 'python' - работает через powershell

setlocal
cd /d "%~dp0"

echo =====================================================
echo Web Server - Python HTTP Server
echo =====================================================
echo.
echo Starting server on http://localhost:8081
echo.
echo Press Ctrl+C to stop the server
echo.

REM Запускаем PowerShell с командой для http сервера
powershell -NoProfile -Command "cd '%cd%'; py -m http.server 8081"

pause
