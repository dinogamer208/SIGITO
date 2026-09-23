"""
utils/sistema.py — Pequeñas diferencias entre sistemas operativos.

SIGITO corre principalmente en Windows, pero el código en sí no debe
tener llamadas específicas de Windows regadas por las vistas: se
centralizan aquí, con su equivalente de Linux/macOS, para que el
proyecto se pueda compilar/correr en otro sistema con solo adaptar
este archivo (y utils/notificaciones.py).
"""

import subprocess
import sys


def abrir_archivo(ruta: str) -> None:
    """
    Abre `ruta` con la aplicación predeterminada del sistema (ej. el
    lector de PDF). Usado por Reportes > "Ver PDF" para el rol
    limitado, que no debe pasar por un diálogo de "guardar como".
    """
    if sys.platform == "win32":
        import os
        os.startfile(ruta)  # noqa: S606 - solo en Windows, ruta generada por la propia app
    elif sys.platform == "darwin":
        subprocess.run(["open", ruta], check=True)
    else:
        subprocess.run(["xdg-open", ruta], check=True)


def area_de_trabajo(ventana) -> tuple[int, int, int, int]:
    """
    (x, y, ancho, alto) del área útil de la pantalla principal, sin la
    barra de tareas, en píxeles reales. En Windows con zoom (ej. 125%),
    Tk reporta el tamaño de pantalla escalado (1536x864) pero posiciona
    las ventanas en píxeles reales (1920x1080), así que se le pregunta
    directo a Windows. En otros sistemas, lo que diga Tk.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            SPI_GETWORKAREA = 0x0030
            if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:  # noqa: BLE001
            pass
    return 0, 0, ventana.winfo_screenwidth(), ventana.winfo_screenheight()
