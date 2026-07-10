"""
controllers/asignacion_controller.py — Lógica de préstamos/devoluciones.

Responsable: Persona 4.

Qué debe hacer este archivo:
1. registrar_prestamo(articulo_id, usuario_id, fecha_devolucion_esperada)
   -> INSERT en `asignaciones` Y llamar a
   inventario_controller.actualizar_estado_articulo(articulo_id, "prestado").
2. registrar_devolucion(asignacion_id) -> UPDATE fecha_devolucion_real
   Y devolver el artículo a estado "disponible".
3. listar_asignaciones_activas() / listar_vencidas() (usa
   Asignacion.esta_vencida() del modelo).

Depende de que existan las tablas de Persona 2 (usuarios) y Persona 3
(articulos) — ver orden recomendado de trabajo.

Esqueleto:
"""

from db.conexion import obtener_conexion
from models.asignacion import Asignacion
from controllers.inventario_controller import actualizar_estado_articulo


def registrar_prestamo(articulo_id: int, usuario_id: int, fecha_devolucion_esperada) -> int:
    # TODO: INSERT INTO asignaciones (...)
    # TODO: actualizar_estado_articulo(articulo_id, "prestado")
    raise NotImplementedError


def registrar_devolucion(asignacion_id: int) -> None:
    # TODO: UPDATE asignaciones SET fecha_devolucion_real = NOW() WHERE id = %s
    # TODO: obtener articulo_id de esa asignación y marcarlo "disponible"
    raise NotImplementedError


def listar_asignaciones_activas() -> list[Asignacion]:
    # TODO: SELECT * FROM asignaciones WHERE fecha_devolucion_real IS NULL
    raise NotImplementedError
