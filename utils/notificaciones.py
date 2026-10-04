"""
utils/notificaciones.py — Notificaciones nativas del sistema operativo.

Windows: winotify (toast). Linux: `notify-send` (libnotify), presente
por defecto en la mayoría de escritorios (GNOME, KDE, XFCE...).
macOS/otros: se ignora en silencio (no hay monitor pensado para correr
ahí todavía).

Si falla por cualquier motivo (Windows viejo, permisos, notify-send no
instalado, servicio de notificaciones apagado) se ignora en silencio —
un aviso que no se pudo mostrar no debe tumbar el monitor de correos
ni ninguna otra parte de la app.
"""

import subprocess
import sys

APP_ID = "SIGITO"


def _mostrar(titulo: str, mensaje: str) -> None:
    try:
        if sys.platform == "win32":
            from winotify import Notification
            Notification(app_id=APP_ID, title=titulo, msg=mensaje).show()
        elif sys.platform.startswith("linux"):
            subprocess.run(
                ["notify-send", "--app-name", APP_ID, titulo, mensaje],
                check=False, timeout=5,
            )
    except Exception:
        pass


def notificar_prestamo_vencido(prestamo: dict) -> None:
    """`prestamo` trae las llaves de asignacion_controller.listar_vencidas_sin_aviso()."""
    _mostrar(
        "Préstamo atrasado — SIGITO",
        f"{prestamo['nombre_completo']} no ha devuelto "
        f"\"{prestamo['articulo_nombre']}\" ({prestamo['codigo_inventario']}).",
    )
