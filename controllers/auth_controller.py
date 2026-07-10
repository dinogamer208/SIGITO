"""
controllers/auth_controller.py — Login, roles y sesión activa.

Responsable: Persona 2.

Qué debe hacer este archivo:
1. iniciar_sesion(correo, password) -> valida contra la tabla usuarios
   usando bcrypt (ver utils/seguridad.py) y devuelve un objeto Usuario
   si las credenciales son correctas, o None/excepción si no.
2. Mantener quién es el usuario activo durante la sesión (variable de
   módulo o clase Sesion simple) para que otras vistas sepan el rol
   actual (ej. ocultar botones de admin a un profesor).
3. cerrar_sesion() -> limpia el estado de sesión activa.

Esqueleto:
"""

from db.conexion import obtener_conexion
from models.usuario import Usuario
from utils.seguridad import verificar_password

_usuario_actual: Usuario | None = None


def iniciar_sesion(correo: str, password: str) -> Usuario | None:
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s AND activo = TRUE", (correo,))
        fila = cursor.fetchone()
        # TODO: si no hay fila -> return None
        # TODO: verificar_password(password, fila["password_hash"])
        # TODO: si es válido, construir Usuario.desde_fila(fila), guardarlo
        #       en _usuario_actual y devolverlo
        raise NotImplementedError
    finally:
        conexion.close()


def cerrar_sesion():
    global _usuario_actual
    _usuario_actual = None


def obtener_usuario_actual() -> Usuario | None:
    return _usuario_actual
