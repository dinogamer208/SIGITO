"""
controllers/auth_controller.py — Login, roles, sesión activa y
catálogo de profesores autorizados.

Responsable: Persona 2.
"""

from db.conexion import cursor_db
from models.usuario import Usuario
from utils.seguridad import verificar_password

_usuario_actual: Usuario | None = None


def iniciar_sesion(usuario: str, password: str) -> Usuario | None:
    with cursor_db(dictionary=True) as cursor:
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = %s AND activo = TRUE",
            (usuario,)
        )
        fila = cursor.fetchone()

    if not fila:
        return None
    if not verificar_password(password, fila["password_hash"]):
        return None

    global _usuario_actual
    _usuario_actual = Usuario.desde_fila(fila)
    return _usuario_actual


def cerrar_sesion():
    global _usuario_actual
    _usuario_actual = None


def obtener_usuario_actual() -> Usuario | None:
    return _usuario_actual


# ---------------------------------------------------------
# Profesores autorizados (catálogo, sin login propio)
# Editable desde Gestión de Usuarios — ver decisiones del README.
# ---------------------------------------------------------

def listar_profesores(solo_activos: bool = True) -> list[dict]:
    query = "SELECT * FROM profesores_autorizados"
    if solo_activos:
        query += " WHERE activo = TRUE"
    query += " ORDER BY nombre_completo"

    with cursor_db(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def agregar_profesor(nombre_completo: str, correo: str, telefono: str = None) -> int:
    with cursor_db(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO profesores_autorizados (nombre_completo, correo, telefono) "
            "VALUES (%s, %s, %s)",
            (nombre_completo, correo, telefono)
        )
        return cursor.lastrowid


def editar_profesor(id_profesor: int, nombre_completo: str, correo: str,
                     telefono: str = None, activo: bool = True) -> None:
    with cursor_db(commit=True) as cursor:
        cursor.execute(
            "UPDATE profesores_autorizados SET nombre_completo = %s, correo = %s, "
            "telefono = %s, activo = %s WHERE id = %s",
            (nombre_completo, correo, telefono, activo, id_profesor)
        )
