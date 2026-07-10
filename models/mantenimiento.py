"""
models/mantenimiento.py — Modelo de datos Mantenimiento.

Responsable: Persona 5.

Qué debe hacer este archivo:
1. Definir una clase Mantenimiento asociada a un artículo, con fecha
   de inicio/fin y descripción del trabajo realizado.
2. Puede incluir esta_activo() para saber si el artículo sigue en
   mantenimiento (fecha_fin es None).

Esqueleto:
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Mantenimiento:
    id: int
    articulo_id: int
    descripcion: str
    fecha_inicio: date
    fecha_fin: Optional[date]

    @staticmethod
    def desde_fila(fila: dict) -> "Mantenimiento":
        # TODO: mapear fila["campo"] -> Mantenimiento(...)
        raise NotImplementedError

    def esta_activo(self) -> bool:
        return self.fecha_fin is None
