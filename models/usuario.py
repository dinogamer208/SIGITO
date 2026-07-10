"""
models/usuario.py — Modelo de datos Usuario.

Responsable: Persona 2.

Qué debe hacer este archivo:
1. Definir una clase Usuario (o dataclass) que represente una fila de
   la tabla `usuarios`, con sus campos y un método desde_fila() para
   construirla a partir de un resultado de MySQL.
2. Este archivo NO debe tener lógica de conexión ni de negocio pesada;
   eso va en controllers/auth_controller.py. Aquí solo se modela el dato.

Esqueleto:
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Usuario:
    id: int
    nombre: str
    correo: str
    rol: str
    activo: bool
    creado_en: datetime = None

    @staticmethod
    def desde_fila(fila: dict) -> "Usuario":
        """Construye un Usuario a partir de un dict (resultado de MySQL)."""
        # TODO: mapear fila["campo"] -> Usuario(...)
        raise NotImplementedError
