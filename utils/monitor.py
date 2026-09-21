"""
utils/monitor.py — Monitor en segundo plano de préstamos atrasados.

Cada 5 minutos revisa las asignaciones vencidas, intenta enviar el
correo de aviso (controllers/config_controller.enviar_correo_atraso) y
siempre dispara una notificación nativa de Windows, para que el aviso
llegue aunque el correo SMTP no esté configurado. Usa la columna
`correo_aviso_enviado` para no avisar dos veces del mismo préstamo.

iniciar()/detener() se llaman desde main.py al entrar y salir del
Dashboard (login/logout/cierre de la app).
"""

import threading

from controllers import asignacion_controller, config_controller
from utils.notificaciones import notificar_prestamo_vencido

INTERVALO_SEGUNDOS = 5 * 60

_detener = threading.Event()
_hilo = None


def _revisar_vencidos():
    asignacion_controller.listar_vencidas()  # deja el estado 'atrasado' al día
    pendientes = asignacion_controller.listar_vencidas_sin_aviso()

    for prestamo in pendientes:
        try:
            config_controller.enviar_correo_atraso(prestamo)
        except Exception:
            pass  # sin SMTP configurado, o falló el envío: igual avisa el toast

        notificar_prestamo_vencido(prestamo)
        asignacion_controller.marcar_aviso_enviado(prestamo["id"])


def _ciclo():
    while not _detener.is_set():
        try:
            _revisar_vencidos()
        except Exception:
            pass  # ej. sin conexión a la BD en este momento: se reintenta solo
        _detener.wait(INTERVALO_SEGUNDOS)


def iniciar():
    """Arranca el monitor si no está ya corriendo (llamar una vez por sesión)."""
    global _hilo
    if _hilo is not None and _hilo.is_alive():
        return
    _detener.clear()
    _hilo = threading.Thread(target=_ciclo, daemon=True)
    _hilo.start()


def detener():
    """Señala al hilo que pare; no bloquea esperándolo (es daemon)."""
    _detener.set()
