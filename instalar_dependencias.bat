@echo off
:: instalar_dependencias.bat - Doble clic para instalar todo lo que
:: necesita el CODIGO FUENTE de SIGITO (esta carpeta) antes de poder
:: correr "python main.py" en una PC nueva.
::
:: Esto es distinto de instalar.bat (ese es para la version empaquetada
:: SIGITO App, que instala el MySQL portatil). Aqui asumimos que ya
:: tienes Python y MySQL instalados en esta PC; esto solo instala las
:: librerias de Python que main.py necesita (customtkinter, etc.).

echo Instalando las dependencias de Python de SIGITO...
echo.

python --version >nul 2>&1
if %errorLevel% NEQ 0 (
    echo No se encontro Python en esta PC.
    echo Instalalo primero desde https://www.python.org/downloads/
    echo ^(marca la casilla "Add python.exe to PATH" durante la instalacion^)
    echo.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"

if %errorLevel% NEQ 0 (
    echo.
    echo Algo fallo instalando las dependencias. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo Listo. Ya puedes correr SIGITO con:  python main.py
echo ^(recuerda copiar .env.example a .env y poner tus datos de MySQL antes^)
echo.
pause
