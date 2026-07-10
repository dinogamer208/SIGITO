"""
controllers/reportes_controller.py — Reportes/estadísticas.

Responsable: Persona 5.

Qué debe hacer este archivo:
1. Consultas de resumen: artículos por estado, préstamos vencidos,
   artículos más prestados, historial por usuario.
2. Delegar la exportación real a utils/exportador.py (PDF/Excel/CSV),
   este archivo solo arma los datos (listas de dicts) que se exportan.
3. Depende de que existan datos en las tablas de Persona 2, 3 y 4.

Esqueleto:
"""

from db.conexion import obtener_conexion


def resumen_articulos_por_estado() -> list[dict]:
    # TODO: SELECT estado, COUNT(*) FROM articulos GROUP BY estado
    raise NotImplementedError


def prestamos_vencidos() -> list[dict]:
    # TODO: SELECT ... JOIN asignaciones/articulos/usuarios
    #       WHERE fecha_devolucion_esperada < NOW() AND fecha_devolucion_real IS NULL
    raise NotImplementedError
