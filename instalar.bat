@echo off
:: instalar.bat - Doble clic en la PC nueva para provisionar la base de
:: datos que SIGITO.exe necesita. Solo hay que correrlo una vez.

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Se necesitan permisos de administrador para instalar el servicio de base de datos.
    echo Volviendo a abrir como administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
echo.
pause
