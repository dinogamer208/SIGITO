"""
models/mantenimiento.py — Modelo de datos Mantenimiento.

Responsable: Persona 5.

Representa una fila de `mantenimientos`: un evento puntual de servicio
sobre un artículo (no un rango con fecha de inicio/fin).
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Mantenimiento:
    id: int
    articulo_id: int
    fecha: date
    descripcion: Optional[str]
    costo: Optional[float]
    tecnico: Optional[str]
    destino: Optional[str] = None
    fecha_retorno_estimada: Optional[date] = None
    estado: str = "en_mantenimiento"

    @staticmethod
    def desde_fila(fila: dict) -> "Mantenimiento":
        return Mantenimiento(
            id=fila["id"],
            articulo_id=fila["articulo_id"],
            fecha=fila["fecha"],
            descripcion=fila.get("descripcion"),
            costo=float(fila["costo"]) if fila.get("costo") is not None else None,
            tecnico=fila.get("tecnico"),
            destino=fila.get("destino"),
            fecha_retorno_estimada=fila.get("fecha_retorno_estimada"),
            estado=fila.get("estado") or "en_mantenimiento",
        )
