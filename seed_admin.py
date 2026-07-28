"""
seed_admin.py — Crea (o resetea la contraseña de) el usuario admin por
defecto: usuario "admin", contraseña "admin123".

Uso:
    python seed_admin.py
"""

from db.conexion import obtener_conexion
from utils.seguridad import hash_password

USUARIO_DEFAULT = "admin"
NOMBRE_DEFAULT = "Administrador"
PASSWORD_DEFAULT = "admin123"


def seed_admin():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    password_hash = hash_password(PASSWORD_DEFAULT)

    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (USUARIO_DEFAULT,))
    existente = cursor.fetchone()

    if existente:
        cursor.execute(
            "UPDATE usuarios SET password_hash = %s, activo = TRUE WHERE usuario = %s",
            (password_hash, USUARIO_DEFAULT)
        )
        print(f"Contraseña del usuario '{USUARIO_DEFAULT}' reseteada a '{PASSWORD_DEFAULT}'.")
    else:
        cursor.execute(
            "INSERT INTO usuarios (nombre, usuario, password_hash, rol, activo) "
            "VALUES (%s, %s, %s, 'admin', TRUE)",
            (NOMBRE_DEFAULT, USUARIO_DEFAULT, password_hash)
        )
        print(f"Usuario admin '{USUARIO_DEFAULT}' creado con contraseña '{PASSWORD_DEFAULT}'.")

    conexion.commit()
    cursor.close()
    conexion.close()


if __name__ == "__main__":
    seed_admin()
