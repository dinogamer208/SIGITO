"""
models/asignacion.py — Modelo de datos Asignación (préstamo/devolución).

Responsable: Persona 4.

Qué debe hacer este archivo:
1. Definir una clase Asignacion con artículo, usuario y fechas de
   préstamo/devolución.
2. Puede incluir una propiedad esta_vencida() que compare la fecha
   esperada de devolución contra la fecha actual (útil para
   controllers/asignacion_controller.py y reportes_controller.py).

Esqueleto:
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Asignacion:
    id: int
    articulo_id: int
    usuario_id: int
    fecha_prestamo: datetime
    fecha_devolucion_esperada: Optional[datetime]
    fecha_devolucion_real: Optional[datetime]

    @staticmethod
    def desde_fila(fila: dict) -> "Asignacion":
        # TODO: mapear fila["campo"] -> Asignacion(...)
        raise NotImplementedError

    def esta_vencida(self) -> bool:
        # TODO: comparar fecha_devolucion_esperada con datetime.now()
        # solo si fecha_devolucion_real todavía es None
        raise NotImplementedError
