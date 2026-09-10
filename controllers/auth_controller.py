"""
controllers/auth_controller.py — Login, roles, sesión activa y
catálogo de profesores autorizados.

Responsable: Persona 2.
"""

from db.conexion import obtener_conexion
from models.usuario import Usuario
from utils.seguridad import hash_password, verificar_password, necesita_rehash

_usuario_actual: Usuario | None = None


def iniciar_sesion(usuario: str, password: str) -> Usuario | None:
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = %s AND activo = TRUE",
            (usuario,)
        )
        fila = cursor.fetchone()
        cursor.close()

        if not fila:
            return None
        if not verificar_password(password, fila["password_hash"]):
            return None

        if necesita_rehash(fila["password_hash"]):
            _regenerar_hash(conexion, fila["id"], password)

        global _usuario_actual
        _usuario_actual = Usuario.desde_fila(fila)
        return _usuario_actual
    finally:
        conexion.close()


def _regenerar_hash(conexion, usuario_id: int, password: str) -> None:
    """
    Reescribe el password_hash del usuario con el costo bcrypt actual.
    El login ya se validó; si el UPDATE falla no se interrumpe la sesión,
    solo se reintentará el rehash en el próximo login.
    """
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (hash_password(password), usuario_id),
        )
        conexion.commit()
        cursor.close()
    except Exception:
        pass


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
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    query = "SELECT * FROM profesores_autorizados"
    if solo_activos:
        query += " WHERE activo = TRUE"
    query += " ORDER BY nombre_completo"
    cursor.execute(query)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def agregar_profesor(nombre_completo: str, correo: str, telefono: str = None) -> int:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO profesores_autorizados (nombre_completo, correo, telefono) "
        "VALUES (%s, %s, %s)",
        (nombre_completo, correo, telefono)
    )
    conexion.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conexion.close()
    return nuevo_id


def editar_profesor(id_profesor: int, nombre_completo: str, correo: str,
                     telefono: str = None, activo: bool = True) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE profesores_autorizados SET nombre_completo = %s, correo = %s, "
        "telefono = %s, activo = %s WHERE id = %s",
        (nombre_completo, correo, telefono, activo, id_profesor)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
