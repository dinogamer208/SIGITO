"""
utils/notificaciones.py — Notificaciones nativas de Windows (toast).

Envoltorio delgado sobre winotify: si falla (Windows viejo, permisos,
servicio de notificaciones apagado) se ignora en silencio — un aviso
que no se pudo mostrar no debe tumbar el monitor de correos ni ninguna
otra parte de la app.
"""

APP_ID = "SIGITO"


def _mostrar(titulo: str, mensaje: str) -> None:
    try:
        from winotify import Notification
        Notification(app_id=APP_ID, title=titulo, msg=mensaje).show()
    except Exception:
        pass


def notificar_prestamo_vencido(prestamo: dict) -> None:
    """`prestamo` trae las llaves de asignacion_controller.listar_vencidas_sin_aviso()."""
    _mostrar(
        "Préstamo atrasado — SIGITO",
        f"{prestamo['nombre_completo']} no ha devuelto "
        f"\"{prestamo['articulo_nombre']}\" ({prestamo['codigo_inventario']}).",
    )
