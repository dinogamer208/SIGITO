"""
controllers/auth_controller.py — Login, roles, sesión activa y
catálogo de profesores autorizados.

Responsable: Persona 2.
"""

from db.conexion import transaccion
from models.usuario import Usuario
from utils.seguridad import hash_password, verificar_password, necesita_rehash

_usuario_actual: Usuario | None = None

LONGITUD_MINIMA_PASSWORD = 6


def iniciar_sesion(usuario: str, password: str) -> Usuario | None:
    # Solo la lectura va dentro de la transacción: el bcrypt (~170 ms) no
    # debe hacerse con una conexión del pool retenida.
    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = %s AND activo = TRUE",
            (usuario,)
        )
        fila = cursor.fetchone()

    if not fila:
        return None
    if not verificar_password(password, fila["password_hash"]):
        return None

    if necesita_rehash(fila["password_hash"]):
        _regenerar_hash(fila["id"], password)

    global _usuario_actual
    _usuario_actual = Usuario.desde_fila(fila)
    return _usuario_actual


def _regenerar_hash(usuario_id: int, password: str) -> None:
    """
    Reescribe el password_hash del usuario con el costo bcrypt actual.
    El login ya se validó; si el UPDATE falla no se interrumpe la sesión,
    solo se reintentará el rehash en el próximo login.
    """
    try:
        with transaccion() as (cursor, _con):
            cursor.execute(
                "UPDATE usuarios SET password_hash = %s WHERE id = %s",
                (hash_password(password), usuario_id),
            )
    except Exception:
        pass


def cerrar_sesion():
    global _usuario_actual
    _usuario_actual = None


def validar_password_nueva(nueva: str, confirmar: str) -> str | None:
    """
    Reglas para una contraseña nueva. Devuelve un mensaje de error, o
    None si es válida. Función pura: sin BD, para poder probarla sola.
    """
    if not nueva:
        return "La nueva contraseña es obligatoria."
    if len(nueva) < LONGITUD_MINIMA_PASSWORD:
        return f"La nueva contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres."
    if nueva != confirmar:
        return "La confirmación no coincide con la nueva contraseña."
    return None


def cambiar_password(usuario_id: int, actual: str, nueva: str, confirmar: str) -> None:
    """
    Cambia la contraseña de login del usuario indicado. Verifica la
    contraseña actual antes de reemplazarla. Lanza ValueError con un
    mensaje claro si algo no cuadra.
    """
    error = validar_password_nueva(nueva, confirmar)
    if error:
        raise ValueError(error)

    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute(
            "SELECT password_hash FROM usuarios WHERE id = %s AND activo = TRUE",
            (usuario_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            raise ValueError("El usuario ya no existe o está inactivo.")
        if not verificar_password(actual, fila["password_hash"]):
            raise ValueError("La contraseña actual es incorrecta.")
        if verificar_password(nueva, fila["password_hash"]):
            raise ValueError("La nueva contraseña no puede ser igual a la actual.")

        cursor.execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (hash_password(nueva), usuario_id),
        )


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

    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute(query)
        return cursor.fetchall()


def agregar_profesor(nombre_completo: str, correo: str, telefono: str = None) -> int:
    with transaccion() as (cursor, _con):
        cursor.execute(
            "INSERT INTO profesores_autorizados (nombre_completo, correo, telefono) "
            "VALUES (%s, %s, %s)",
            (nombre_completo, correo, telefono)
        )
        return cursor.lastrowid


def editar_profesor(id_profesor: int, nombre_completo: str, correo: str,
                     telefono: str = None, activo: bool = True) -> None:
    with transaccion() as (cursor, _con):
        cursor.execute(
            "UPDATE profesores_autorizados SET nombre_completo = %s, correo = %s, "
            "telefono = %s, activo = %s WHERE id = %s",
            (nombre_completo, correo, telefono, activo, id_profesor)
        )
