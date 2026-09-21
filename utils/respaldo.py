"""
utils/respaldo.py — Respaldo automático periódico del inventario.

Si está activado desde Configuración, cada N horas genera un .zip con
el inventario y sus fotos (mismo formato que "Descargar con fotos" en
Configuración) en la carpeta backups/, y borra los respaldos más
viejos para no acumular espacio indefinidamente.

iniciar()/detener() se llaman desde main.py al entrar y salir del
Dashboard (login/logout/cierre de la app), igual que utils/monitor.py.
"""

import glob
import os
import threading
from datetime import datetime

from controllers import config_controller, inventario_controller
from utils.exportador import exportar_inventario_zip

CARPETA_RESPALDOS = "backups"
MAXIMO_RESPALDOS = 10
INTERVALO_REVISION_INACTIVO = 5 * 60  # revisa cada 5 min si se activó desde Configuración

_detener = threading.Event()
_hilo = None


def _generar_respaldo():
    datos = inventario_controller.datos_para_exportar(incluir_foto_path=True)
    if not datos:
        return

    os.makedirs(CARPETA_RESPALDOS, exist_ok=True)
    nombre = f"inventario_{datetime.now():%Y%m%d_%H%M%S}.zip"
    exportar_inventario_zip(datos, os.path.join(CARPETA_RESPALDOS, nombre))

    respaldos = sorted(glob.glob(os.path.join(CARPETA_RESPALDOS, "inventario_*.zip")))
    for viejo in respaldos[:-MAXIMO_RESPALDOS]:
        try:
            os.remove(viejo)
        except OSError:
            pass


def _ciclo():
    while not _detener.is_set():
        try:
            ajuste = config_controller.obtener_ajuste_respaldo()
        except Exception:
            ajuste = None

        if not ajuste or not ajuste["activo"]:
            _detener.wait(INTERVALO_REVISION_INACTIVO)
            continue

        try:
            _generar_respaldo()
        except Exception:
            pass  # un fallo puntual (ej. sin conexión) no debe tumbar el respaldo
        _detener.wait(ajuste["intervalo_horas"] * 3600)


def iniciar():
    """Arranca el hilo de respaldo si no está ya corriendo (llamar una
    vez por sesión; no hace nada si `activo` sigue en falso — el hilo
    solo queda revisando el ajuste cada 5 min)."""
    global _hilo
    if _hilo is not None and _hilo.is_alive():
        return
    _detener.clear()
    _hilo = threading.Thread(target=_ciclo, daemon=True)
    _hilo.start()


def detener():
    """Señala al hilo que pare; no bloquea esperándolo (es daemon)."""
    _detener.set()
