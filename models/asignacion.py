"""
models/asignacion.py — Modelo de datos Asignación (préstamo/devolución).

Responsable: Persona 4.

Representa una fila de `asignaciones`. El alumno no tiene login propio,
así que sus datos (nombre, sección, año, teléfono, correo) se guardan
directamente en la asignación en vez de una FK a `usuarios`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Asignacion:
    id: int
    articulo_id: int
    nombre_completo: str
    seccion: str
    anio: str
    telefono: str
    correo: str
    foto_alumno: Optional[str]
    profesor_autoriza_id: int
    hora_salida: datetime
    hora_estimada_devolucion: datetime
    hora_entrada_real: Optional[datetime]
    estado: str
    correo_aviso_enviado: bool
    usuario_registro_id: int
    usuario_devolucion_id: Optional[int]
    fecha_creacion: Optional[datetime] = None

    @staticmethod
    def desde_fila(fila: dict) -> "Asignacion":
        return Asignacion(
            id=fila["id"],
            articulo_id=fila["articulo_id"],
            nombre_completo=fila["nombre_completo"],
            seccion=fila["seccion"],
            anio=fila["anio"],
            telefono=fila["telefono"],
            correo=fila["correo"],
            foto_alumno=fila.get("foto_alumno"),
            profesor_autoriza_id=fila["profesor_autoriza_id"],
            hora_salida=fila["hora_salida"],
            hora_estimada_devolucion=fila["hora_estimada_devolucion"],
            hora_entrada_real=fila.get("hora_entrada_real"),
            estado=fila["estado"],
            correo_aviso_enviado=bool(fila["correo_aviso_enviado"]),
            usuario_registro_id=fila["usuario_registro_id"],
            usuario_devolucion_id=fila.get("usuario_devolucion_id"),
            fecha_creacion=fila.get("fecha_creacion"),
        )

    def esta_vencida(self) -> bool:
        if self.hora_entrada_real is not None:
            return False
        return datetime.now() > self.hora_estimada_devolucion
