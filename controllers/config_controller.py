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
from db.conexion import transaccion
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
    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute("SELECT clave, valor FROM configuracion")
        filas = {fila["clave"]: fila["valor"] for fila in cursor.fetchall()}

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

    with transaccion() as (cursor, _con):
        cursor.executemany(
            "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
            list(cambios.items()),
        )


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
