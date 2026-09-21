"""
controllers/config_controller.py — Ajustes editables desde la app.

Responsable: Persona 4 (correos/notificaciones) + Persona 5 (pantalla).

Lee y guarda la tabla `configuracion` (pares clave/valor). Hoy cubre el
correo remitente de los avisos de atraso, la contraseña de aplicación
SMTP (guardada CIFRADA con Fernet) y un correo de copia al administrador.

El monitor de correos cada 5 min (pendiente, ver README) debe leer estos
valores con obtener_config() en vez de config.py, para que el equipo los
cambie sin tocar código.
"""

import re
import smtplib
import ssl
from email.message import EmailMessage

from config import SMTP_HOST, SMTP_PORT
from db.conexion import obtener_conexion
from utils.seguridad import cifrar, descifrar

_CLAVES = ("correo_remitente", "smtp_app_password", "correo_copia_admin")
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def correo_valido(correo: str) -> bool:
    """True si `correo` tiene forma de dirección de correo. '' se considera inválido."""
    return bool(_RE_CORREO.match((correo or "").strip()))


def obtener_config() -> dict:
    """
    Devuelve {clave: valor} para todas las claves conocidas. La
    contraseña SMTP se devuelve YA descifrada y lista para usar.
    Las claves que aún no existan en la BD vuelven como "".
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT clave, valor FROM configuracion")
    filas = {fila["clave"]: fila["valor"] for fila in cursor.fetchall()}
    cursor.close()
    conexion.close()

    datos = {clave: (filas.get(clave) or "") for clave in _CLAVES}
    datos["smtp_app_password"] = descifrar(datos["smtp_app_password"])
    return datos


def guardar_config(correo_remitente: str, correo_copia_admin: str,
                   smtp_app_password: str | None = None) -> None:
    """
    Guarda los ajustes. `smtp_app_password=None` deja la contraseña
    actual sin cambios (útil cuando el usuario no reescribe ese campo);
    una cadena vacía SÍ borra la contraseña guardada.

    Lanza ValueError si algún correo con contenido tiene formato inválido.
    """
    correo_remitente = (correo_remitente or "").strip()
    correo_copia_admin = (correo_copia_admin or "").strip()

    if correo_remitente and not correo_valido(correo_remitente):
        raise ValueError("El correo remitente no tiene un formato válido.")
    if correo_copia_admin and not correo_valido(correo_copia_admin):
        raise ValueError("El correo de copia al administrador no tiene un formato válido.")

    cambios = {
        "correo_remitente": correo_remitente,
        "correo_copia_admin": correo_copia_admin,
    }
    if smtp_app_password is not None:
        cambios["smtp_app_password"] = cifrar(smtp_app_password.strip())

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.executemany(
        "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
        list(cambios.items()),
    )
    conexion.commit()
    cursor.close()
    conexion.close()


_CLAVES_RESPALDO = ("respaldo_automatico_activo", "respaldo_intervalo_horas")


def obtener_ajuste_respaldo() -> dict:
    """
    Devuelve {"activo": bool, "intervalo_horas": int} para el respaldo
    automático del inventario (utils/respaldo.py). Si nunca se guardó,
    vuelve el default: desactivado, cada 24 horas.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT clave, valor FROM configuracion WHERE clave IN (%s, %s)",
        _CLAVES_RESPALDO,
    )
    filas = {fila["clave"]: fila["valor"] for fila in cursor.fetchall()}
    cursor.close()
    conexion.close()

    try:
        intervalo = int(filas.get("respaldo_intervalo_horas") or 24)
    except ValueError:
        intervalo = 24

    return {
        "activo": filas.get("respaldo_automatico_activo") == "true",
        "intervalo_horas": max(1, intervalo),
    }


def guardar_ajuste_respaldo(activo: bool, intervalo_horas: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.executemany(
        "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
        [
            ("respaldo_automatico_activo", "true" if activo else "false"),
            ("respaldo_intervalo_horas", str(max(1, int(intervalo_horas)))),
        ],
    )
    conexion.commit()
    cursor.close()
    conexion.close()


_CLAVES_SOPORTE = ("soporte_telefono", "soporte_coordinador", "soporte_correo")


def obtener_contacto_soporte() -> dict:
    """
    Datos de contacto que se muestran a un usuario 'limitado' cuando no
    tiene forma de recuperar su contraseña por sí solo (ver
    Configuración > Recuperación de cuenta > Contacto de soporte).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT clave, valor FROM configuracion WHERE clave IN (%s, %s, %s)",
        _CLAVES_SOPORTE,
    )
    filas = {fila["clave"]: fila["valor"] for fila in cursor.fetchall()}
    cursor.close()
    conexion.close()
    return {clave: (filas.get(clave) or "") for clave in _CLAVES_SOPORTE}


def guardar_contacto_soporte(telefono: str, coordinador: str, correo: str) -> None:
    correo = (correo or "").strip()
    if correo and not correo_valido(correo):
        raise ValueError("El correo de soporte no tiene un formato válido.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.executemany(
        "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
        [
            ("soporte_telefono", (telefono or "").strip()),
            ("soporte_coordinador", (coordinador or "").strip()),
            ("soporte_correo", correo),
        ],
    )
    conexion.commit()
    cursor.close()
    conexion.close()


def enviar_correo_codigo_recuperacion(destino: str, codigo: str) -> None:
    """Envía el código temporal de recuperación de contraseña (ver
    auth_controller.solicitar_codigo_recuperacion_por_correo)."""
    cfg = obtener_config()
    remitente = cfg["correo_remitente"]
    password = cfg["smtp_app_password"]

    if not remitente or not password:
        raise ValueError("Falta configurar el correo remitente y/o la contraseña de aplicación.")

    mensaje = EmailMessage()
    mensaje["Subject"] = "SIGITO — Código para recuperar tu contraseña"
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje.set_content(
        f"Tu código para recuperar la contraseña de SIGITO es:\n\n{codigo}\n\n"
        "Vence en 30 minutos. Si no lo pediste tú, ignora este correo."
    )

    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contexto, timeout=15) as servidor:
        servidor.login(remitente, password)
        servidor.send_message(mensaje)


_TABLAS_A_BORRAR = (
    "historial_movimientos", "mantenimientos", "asignaciones",
    "articulos", "categorias", "profesores_autorizados", "configuracion",
)


def reiniciar_base_datos() -> None:
    """
    Borra TODOS los datos operativos: inventario, categorías, préstamos,
    historial de movimientos, mantenimientos, profesores autorizados y
    la configuración de correo. Deja las tablas vacías pero con su
    estructura intacta.

    Deliberadamente NO toca `usuarios`, para que quien ejecutó el
    borrado pueda seguir iniciando sesión después.

    Irreversible. La pantalla que llama a esto es responsable de pedir
    la contraseña y una doble confirmación antes de invocarla.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tabla in _TABLAS_A_BORRAR:
        cursor.execute(f"TRUNCATE TABLE {tabla}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conexion.commit()
    cursor.close()
    conexion.close()


def enviar_correo_prueba(destino: str | None = None) -> str:
    """
    Envía un correo de prueba usando la configuración guardada para
    verificar que el remitente y la contraseña de aplicación funcionan.

    Devuelve la dirección a la que se envió. Lanza ValueError si falta
    configuración, o la excepción de smtplib si el servidor la rechaza.
    """
    cfg = obtener_config()
    remitente = cfg["correo_remitente"]
    password = cfg["smtp_app_password"]

    if not remitente or not password:
        raise ValueError(
            "Falta configurar el correo remitente y/o la contraseña de aplicación."
        )

    destino = (destino or cfg["correo_copia_admin"] or remitente).strip()
    if not correo_valido(destino):
        raise ValueError("No hay una dirección de destino válida para la prueba.")

    mensaje = EmailMessage()
    mensaje["Subject"] = "SIGITO — correo de prueba"
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje.set_content(
        "Este es un correo de prueba enviado desde la pantalla de "
        "Configuración de SIGITO.\n\n"
        "Si lo recibiste, el envío de avisos de atraso está listo."
    )

    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contexto, timeout=15) as servidor:
        servidor.login(remitente, password)
        servidor.send_message(mensaje)

    return destino


def enviar_correo_atraso(prestamo: dict) -> None:
    """
    Envía el aviso de atraso de un préstamo puntual (alumno + copia al
    administrador si hay uno configurado). `prestamo` trae las llaves de
    asignacion_controller.listar_vencidas_sin_aviso(): nombre_completo,
    seccion, anio, correo, codigo_inventario, articulo_nombre,
    hora_estimada_devolucion.

    Lanza ValueError si no hay SMTP configurado, o la excepción de
    smtplib si el envío falla; quien llame decide si eso detiene el
    aviso (utils/monitor.py igual dispara la notificación nativa).
    """
    cfg = obtener_config()
    remitente = cfg["correo_remitente"]
    password = cfg["smtp_app_password"]

    if not remitente or not password:
        raise ValueError("Falta configurar el correo remitente y/o la contraseña de aplicación.")
    if not correo_valido(prestamo.get("correo") or ""):
        raise ValueError(f"El préstamo #{prestamo.get('id')} no tiene un correo válido.")

    mensaje = EmailMessage()
    mensaje["Subject"] = f"SIGITO — Préstamo atrasado: {prestamo['articulo_nombre']}"
    mensaje["From"] = remitente
    mensaje["To"] = prestamo["correo"]
    if cfg["correo_copia_admin"]:
        mensaje["Cc"] = cfg["correo_copia_admin"]

    mensaje.set_content(
        f"Hola {prestamo['nombre_completo']},\n\n"
        f"El artículo \"{prestamo['articulo_nombre']}\" ({prestamo['codigo_inventario']}) "
        f"que tienes prestado ({prestamo['seccion']} {prestamo['anio']}) debió devolverse "
        f"el {prestamo['hora_estimada_devolucion']:%Y-%m-%d %H:%M} y todavía no se ha "
        "registrado su devolución.\n\n"
        "Por favor devuélvelo lo antes posible.\n\n"
        "Este es un aviso automático de SIGITO."
    )

    destinatarios = [prestamo["correo"]] + ([cfg["correo_copia_admin"]] if cfg["correo_copia_admin"] else [])

    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contexto, timeout=15) as servidor:
        servidor.login(remitente, password)
        servidor.send_message(mensaje, to_addrs=destinatarios)
