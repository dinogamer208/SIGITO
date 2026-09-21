"""
controllers/auth_controller.py — Login, roles, sesión activa y
catálogo de profesores autorizados.

Responsable: Persona 2.
"""

import re
import secrets
from datetime import datetime, timedelta

from db.conexion import obtener_conexion
from models.usuario import Usuario
from utils.seguridad import hash_password, verificar_password, necesita_rehash

_usuario_actual: Usuario | None = None

LONGITUD_MINIMA_PASSWORD = 6
ROLES_VALIDOS = ("admin", "limitado")
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT password_hash FROM usuarios WHERE id = %s AND activo = TRUE",
            (usuario_id,),
        )
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            raise ValueError("El usuario ya no existe o está inactivo.")
        if not verificar_password(actual, fila["password_hash"]):
            cursor.close()
            raise ValueError("La contraseña actual es incorrecta.")
        if verificar_password(nueva, fila["password_hash"]):
            cursor.close()
            raise ValueError("La nueva contraseña no puede ser igual a la actual.")

        cursor.execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (hash_password(nueva), usuario_id),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def obtener_usuario_actual() -> Usuario | None:
    return _usuario_actual


def verificar_password_usuario(usuario_id: int, password: str) -> bool:
    """
    Revalida la contraseña de un usuario ya autenticado, sin abrir una
    sesión nueva. Se usa para reconfirmar identidad antes de una acción
    destructiva (ej. borrar la base de datos desde Configuración).
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT password_hash FROM usuarios WHERE id = %s AND activo = TRUE",
            (usuario_id,),
        )
        fila = cursor.fetchone()
        cursor.close()
        if not fila:
            return False
        return verificar_password(password, fila["password_hash"])
    finally:
        conexion.close()


def verificar_password_admin(password: str) -> bool:
    """
    True si `password` coincide con la contraseña de ALGÚN usuario con
    rol 'admin' activo. Se usa para autorizar acciones que un usuario
    'limitado' no puede hacer por sí solo, ej. cambiar su propia
    contraseña (necesita que un admin la autorice tecleándola).
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT password_hash FROM usuarios WHERE rol = 'admin' AND activo = TRUE"
        )
        return any(
            verificar_password(password, fila["password_hash"])
            for fila in cursor.fetchall()
        )
    finally:
        conexion.close()


def cambiar_password_autorizado_por_admin(usuario_id: int, password_admin: str,
                                           nueva: str, confirmar: str) -> None:
    """
    Cambia la contraseña de `usuario_id` (pensado para un usuario
    'limitado' cambiando la suya propia) pero en vez de pedir SU
    contraseña actual, exige la de un administrador como autorización.
    """
    error = validar_password_nueva(nueva, confirmar)
    if error:
        raise ValueError(error)
    if not verificar_password_admin(password_admin):
        raise ValueError("La contraseña del administrador es incorrecta.")

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (hash_password(nueva), usuario_id),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def listar_usuarios() -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nombre, usuario, rol, activo FROM usuarios ORDER BY id"
    )
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def agregar_usuario(nombre: str, usuario: str, password: str, rol: str) -> int:
    """
    Crea un nuevo usuario de login (además del admin inicial). Pensado
    para llamarse desde Configuración > Agregar usuario (solo admin).
    """
    nombre = (nombre or "").strip()
    usuario = (usuario or "").strip()

    if not nombre or not usuario:
        raise ValueError("Nombre y nombre de usuario son obligatorios.")
    if len(password or "") < LONGITUD_MINIMA_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres.")
    if rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol inválido: {rol}")

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Ya existe un usuario con el nombre de usuario '{usuario}'.")

        cursor.execute(
            "INSERT INTO usuarios (nombre, usuario, password_hash, rol, activo) "
            "VALUES (%s, %s, %s, %s, TRUE)",
            (nombre, usuario, hash_password(password), rol),
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid
        cursor.close()
        return nuevo_id
    finally:
        conexion.close()


def _hay_otro_admin_activo(cursor, usuario_id_excluido: int) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = TRUE AND id != %s",
        (usuario_id_excluido,)
    )
    return cursor.fetchone()[0] > 0


def restablecer_password_admin(usuario_id: int, nueva_password: str) -> None:
    """
    El admin le asigna una contraseña nueva a OTRO usuario directamente
    (sin pedir la contraseña anterior de ese usuario — el admin ya se
    autenticó para entrar a Configuración). Pensado para el botón
    "Restablecer contraseña" en Agregar usuario.
    """
    if len(nueva_password or "") < LONGITUD_MINIMA_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres.")

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s WHERE id = %s",
            (hash_password(nueva_password), usuario_id),
        )
        if cursor.rowcount == 0:
            cursor.close()
            raise ValueError(f"No existe el usuario id={usuario_id}")
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def cambiar_estado_usuario(usuario_id: int, activo: bool) -> None:
    """
    Activa o desactiva un usuario. Un usuario desactivado no puede
    iniciar sesión (iniciar_sesion ya filtra WHERE activo = TRUE) — es
    la forma de "quitarle la contraseña y dejarlo sin acceso" sin
    permitir un login sin contraseña real.

    No se puede desactivar al único admin activo que quede.
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        if not activo:
            cursor.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
            fila = cursor.fetchone()
            if fila and fila[0] == "admin" and not _hay_otro_admin_activo(cursor, usuario_id):
                cursor.close()
                raise ValueError("No puedes desactivar al único administrador activo.")

        cursor.execute(
            "UPDATE usuarios SET activo = %s WHERE id = %s",
            (activo, usuario_id),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def eliminar_usuario(usuario_id: int) -> None:
    """
    Borra un usuario por completo. Solo funciona si nunca registró
    préstamos/devoluciones ni aparece en el historial de auditoría
    (asignaciones.usuario_registro_id/usuario_devolucion_id e
    historial_movimientos.usuario_id son FOREIGN KEY hacia usuarios);
    si ya se usó, hay que desactivarlo en vez de borrarlo, para no
    perder ese rastro.

    No se puede eliminar al único administrador activo.
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()

        cursor.execute("SELECT rol, activo FROM usuarios WHERE id = %s", (usuario_id,))
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            raise ValueError(f"No existe el usuario id={usuario_id}")
        rol, activo = fila
        if rol == "admin" and activo and not _hay_otro_admin_activo(cursor, usuario_id):
            cursor.close()
            raise ValueError("No puedes eliminar al único administrador activo.")

        cursor.execute(
            "SELECT COUNT(*) FROM asignaciones "
            "WHERE usuario_registro_id = %s OR usuario_devolucion_id = %s",
            (usuario_id, usuario_id)
        )
        en_asignaciones = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM historial_movimientos WHERE usuario_id = %s",
            (usuario_id,)
        )
        en_historial = cursor.fetchone()[0]

        if en_asignaciones or en_historial:
            cursor.close()
            raise ValueError(
                "No se puede eliminar: este usuario ya tiene actividad registrada "
                "(préstamos y/o historial). Desactívalo en su lugar."
            )

        cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


# ---------------------------------------------------------
# Recuperación de cuenta, 100% local (sin tocar la BD a mano):
# 1. Código de recuperación permanente, generado desde Configuración
#    (solo admin lo ve/genera) y usado desde el login si se olvida la
#    contraseña.
# 2. Código temporal de un solo uso enviado por correo, si el usuario
#    tiene un correo registrado y hay SMTP configurado.
#
# Ambos comparten un límite de intentos fallidos (por cuenta, sin
# importar el método) para que no se pueda adivinar un código a fuerza
# bruta: MAX_INTENTOS_RECUPERACION seguidos y se bloquea por
# BLOQUEO_RECUPERACION_MINUTOS — no de forma permanente, para no dejar
# a un admin sin ninguna forma de entrar si se equivoca varias veces
# con su propio código.
# ---------------------------------------------------------

MAX_INTENTOS_RECUPERACION = 5
BLOQUEO_RECUPERACION_MINUTOS = 15


def _chequear_bloqueo_recuperacion(fila: dict) -> None:
    bloqueado_hasta = fila.get("recovery_bloqueado_hasta")
    if bloqueado_hasta and bloqueado_hasta > datetime.now():
        minutos = max(1, int((bloqueado_hasta - datetime.now()).total_seconds() // 60) + 1)
        raise ValueError(
            f"Demasiados intentos fallidos. Espera {minutos} minuto(s) antes de volver a intentar."
        )


def _registrar_intento_fallido_recuperacion(usuario_id: int) -> None:
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET recovery_intentos_fallidos = recovery_intentos_fallidos + 1 "
            "WHERE id = %s",
            (usuario_id,)
        )
        cursor.execute(
            "UPDATE usuarios SET recovery_bloqueado_hasta = %s "
            "WHERE id = %s AND recovery_intentos_fallidos >= %s",
            (datetime.now() + timedelta(minutes=BLOQUEO_RECUPERACION_MINUTOS),
             usuario_id, MAX_INTENTOS_RECUPERACION)
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def _resetear_intentos_recuperacion(usuario_id: int) -> None:
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET recovery_intentos_fallidos = 0, recovery_bloqueado_hasta = NULL "
            "WHERE id = %s",
            (usuario_id,)
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def generar_codigo_recuperacion(usuario_id: int) -> str:
    """
    Genera (o reemplaza) el código de recuperación permanente de
    `usuario_id` y lo devuelve EN TEXTO PLANO — es la única vez que se
    puede ver; se guarda hasheado, igual que una contraseña. De paso
    limpia cualquier bloqueo por intentos fallidos anterior.
    """
    codigo = "-".join(secrets.token_hex(2).upper() for _ in range(4))  # ej. AB12-CD34-EF56-1A2B

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET recovery_code_hash = %s, recovery_intentos_fallidos = 0, "
            "recovery_bloqueado_hasta = NULL WHERE id = %s",
            (hash_password(codigo), usuario_id),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()

    return codigo


def tiene_codigo_recuperacion(usuario_id: int) -> bool:
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT recovery_code_hash FROM usuarios WHERE id = %s", (usuario_id,))
        fila = cursor.fetchone()
        return bool(fila and fila[0])
    finally:
        conexion.close()


def recuperar_con_codigo(usuario: str, codigo: str, nueva: str, confirmar: str) -> None:
    """
    "Olvidé mi contraseña" con el código de recuperación. De un solo
    uso: si funciona, se borra (hay que generar uno nuevo para la
    próxima vez que se necesite).
    """
    error = validar_password_nueva(nueva, confirmar)
    if error:
        raise ValueError(error)

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, recovery_code_hash, recovery_bloqueado_hasta FROM usuarios "
            "WHERE usuario = %s AND activo = TRUE",
            (usuario,)
        )
        fila = cursor.fetchone()
        cursor.close()
        if not fila or not fila["recovery_code_hash"]:
            raise ValueError("Este usuario no tiene un código de recuperación configurado.")

        _chequear_bloqueo_recuperacion(fila)

        if not verificar_password(codigo, fila["recovery_code_hash"]):
            _registrar_intento_fallido_recuperacion(fila["id"])
            raise ValueError("El código de recuperación es incorrecto.")

        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s, recovery_code_hash = NULL, "
            "recovery_intentos_fallidos = 0, recovery_bloqueado_hasta = NULL WHERE id = %s",
            (hash_password(nueva), fila["id"]),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def actualizar_correo(usuario_id: int, correo: str) -> None:
    """Correo de recuperación del usuario (distinto del correo de avisos
    de atraso, que es de la app en general, no de una cuenta)."""
    correo = (correo or "").strip()
    if correo and not _RE_CORREO.match(correo):
        raise ValueError("El correo no tiene un formato válido.")

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET correo = %s WHERE id = %s", (correo or None, usuario_id)
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


def solicitar_codigo_recuperacion_por_correo(usuario: str) -> str:
    """
    Genera un código temporal de 6 dígitos (válido 30 min), lo guarda
    hasheado y lo envía al correo registrado de `usuario`. Devuelve ese
    correo (para mostrarlo en la UI, ej. "enviado a ana***@gmail.com").

    Lanza ValueError si el usuario no existe/está desactivado, no tiene
    correo registrado, o no hay SMTP configurado en Configuración.
    """
    from controllers import config_controller  # import local: evita ciclo a nivel de módulo

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, correo FROM usuarios WHERE usuario = %s AND activo = TRUE", (usuario,)
        )
        fila = cursor.fetchone()
        if not fila:
            cursor.close()
            raise ValueError("No existe ese usuario, o está desactivado.")
        if not fila["correo"]:
            cursor.close()
            raise ValueError("Este usuario no tiene un correo de recuperación registrado.")

        codigo = f"{secrets.randbelow(1_000_000):06d}"
        expira = datetime.now() + timedelta(minutes=30)
        cursor.execute(
            "UPDATE usuarios SET recovery_email_code_hash = %s, recovery_email_code_expira = %s "
            "WHERE id = %s",
            (hash_password(codigo), expira, fila["id"]),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()

    config_controller.enviar_correo_codigo_recuperacion(fila["correo"], codigo)
    return fila["correo"]


def recuperar_con_codigo_correo(usuario: str, codigo: str, nueva: str, confirmar: str) -> None:
    error = validar_password_nueva(nueva, confirmar)
    if error:
        raise ValueError(error)

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, recovery_email_code_hash, recovery_email_code_expira, "
            "recovery_bloqueado_hasta FROM usuarios WHERE usuario = %s AND activo = TRUE",
            (usuario,)
        )
        fila = cursor.fetchone()
        cursor.close()
        if not fila or not fila["recovery_email_code_hash"]:
            raise ValueError("No hay un código pendiente para este usuario. Pide uno nuevo.")

        _chequear_bloqueo_recuperacion(fila)

        if fila["recovery_email_code_expira"] and fila["recovery_email_code_expira"] < datetime.now():
            raise ValueError("El código expiró. Pide uno nuevo.")
        if not verificar_password(codigo, fila["recovery_email_code_hash"]):
            _registrar_intento_fallido_recuperacion(fila["id"])
            raise ValueError("El código es incorrecto.")

        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s, recovery_email_code_hash = NULL, "
            "recovery_email_code_expira = NULL, recovery_intentos_fallidos = 0, "
            "recovery_bloqueado_hasta = NULL WHERE id = %s",
            (hash_password(nueva), fila["id"]),
        )
        conexion.commit()
        cursor.close()
    finally:
        conexion.close()


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
