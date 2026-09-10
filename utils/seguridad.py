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


# --- Cifrado opcional con Fernet (solo si se guarda algo sensible en BD) ---
# from cryptography.fernet import Fernet
#
# def cargar_llave(ruta="/etc/sigito/secret.key") -> bytes:
#     # TODO: leer bytes de la llave desde un archivo fuera del repo
#     raise NotImplementedError
#
# def cifrar(texto: str, llave: bytes) -> bytes:
#     return Fernet(llave).encrypt(texto.encode("utf-8"))
#
# def descifrar(token: bytes, llave: bytes) -> str:
#     return Fernet(llave).decrypt(token).decode("utf-8")
