"""
models/usuario.py — Modelo de datos Usuario.

Responsable: Persona 2.

Qué debe hacer este archivo:
1. Definir una clase Usuario (o dataclass) que represente una fila de
   la tabla `usuarios`, con sus campos y un método desde_fila() para
   construirla a partir de un resultado de MySQL.
2. Este archivo NO debe tener lógica de conexión ni de negocio pesada;
   eso va en controllers/auth_controller.py. Aquí solo se modela el dato.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    rol: str
    activo: bool
    fecha_creacion: datetime = None

    @staticmethod
    def desde_fila(fila: dict) -> "Usuario":
        """Construye un Usuario a partir de un dict (resultado de MySQL).
        No incluye password_hash: nadie fuera de auth_controller debe
        cargar el hash en memoria más tiempo del necesario."""
        return Usuario(
            id=fila["id"],
            nombre=fila["nombre"],
            usuario=fila["usuario"],
            rol=fila["rol"],
            activo=bool(fila["activo"]),
            fecha_creacion=fila.get("fecha_creacion"),
        )
