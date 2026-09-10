"""
utils/seguridad.py — Hash de contraseñas y cifrado (Fernet si se usa).

Responsable: compartido (principalmente Persona 2 para login).

Qué debe hacer este archivo:
1. hash_password(password) / verificar_password(password, hash) usando
   bcrypt — usado por auth_controller.py.
2. Si se decide guardar credenciales sensibles en la BD (ej. contraseña
   de aplicación de Gmail para reportes.py), usar cryptography.Fernet
   igual que se hizo en Café Nova: llave en un archivo fuera del
   repositorio (ej. /etc/sigito/secret.key), nunca en config.py.

Esqueleto:
"""

import os
from pathlib import Path

import bcrypt

# Costo (log2 de iteraciones) de bcrypt. El default de la librería es 12
# (~650 ms al validar en un PC del laboratorio), y eso se sentía como
# demora en cada login. 10 (~65 ms) sigue siendo razonable para un
# sistema interno de un solo rol admin. Los hashes viejos con otro costo
# se regeneran solos en el siguiente login correcto (ver
# auth_controller.iniciar_sesion -> necesita_rehash).
COSTO_BCRYPT = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(COSTO_BCRYPT)
    ).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def necesita_rehash(password_hash: str) -> bool:
    """
    True si el hash guardado usa un costo distinto al actual (COSTO_BCRYPT)
    y conviene regenerarlo. Formato bcrypt: ``$2b$<costo>$<sal+hash>``.
    Ante cualquier formato raro devuelve False (no forzar rehash a ciegas).
    """
    partes = password_hash.split("$")
    if len(partes) < 4:
        return False
    try:
        return int(partes[2]) != COSTO_BCRYPT
    except ValueError:
        return False


# ---------------------------------------------------------
# Cifrado simétrico con Fernet
# ---------------------------------------------------------
# Se usa para guardar en la BD la contraseña de aplicación de Gmail
# (SMTP) que la pantalla de Configuración deja escribir. La llave NO
# vive en el repo ni en config.py: se guarda en un archivo del equipo
# (~/.sigito/secret.key por defecto, o la ruta de SIGITO_SECRET_KEY) y
# se genera sola la primera vez que se necesita.
#
# Si mueves el proyecto a otra PC y quieres conservar los valores
# cifrados, copia también ese archivo secret.key.

def ruta_llave() -> Path:
    """Ruta del archivo de llave Fernet (configurable con SIGITO_SECRET_KEY)."""
    ruta = os.getenv("SIGITO_SECRET_KEY")
    if ruta:
        return Path(ruta)
    return Path.home() / ".sigito" / "secret.key"


def cargar_llave() -> bytes:
    """
    Devuelve la llave Fernet en bytes. La crea (y su carpeta) la
    primera vez con permisos restringidos al usuario cuando el SO lo
    permite.
    """
    from cryptography.fernet import Fernet

    ruta = ruta_llave()
    if ruta.exists():
        return ruta.read_bytes().strip()

    ruta.parent.mkdir(parents=True, exist_ok=True)
    llave = Fernet.generate_key()
    ruta.write_bytes(llave)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass  # Windows sin soporte de chmod POSIX: no es crítico
    return llave


def cifrar(texto: str) -> str:
    """Cifra un texto y devuelve el token como str (para guardar en la BD)."""
    from cryptography.fernet import Fernet

    if texto == "":
        return ""
    return Fernet(cargar_llave()).encrypt(texto.encode("utf-8")).decode("utf-8")


def descifrar(token: str) -> str:
    """Descifra un token generado por cifrar(). Devuelve '' si el token está vacío."""
    from cryptography.fernet import Fernet

    if not token:
        return ""
    return Fernet(cargar_llave()).decrypt(token.encode("utf-8")).decode("utf-8")
