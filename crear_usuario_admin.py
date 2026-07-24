"""
crear_usuario_admin.py — Crea el primer usuario admin.

La tabla `usuarios` viene vacía en seed_data.sql (no se pueden meter
contraseñas ya hasheadas a mano en SQL). Corre este script una vez
después de aplicar db/schema.sql para poder iniciar sesión.

Uso:
    python crear_usuario_admin.py
"""

import getpass

from db.conexion import obtener_conexion
from utils.seguridad import hash_password


def crear_admin(nombre, usuario, password):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
    if cursor.fetchone():
        cursor.close()
        conexion.close()
        print(f"Ya existe un usuario con el nombre de usuario '{usuario}'.")
        return

    cursor.execute(
        "INSERT INTO usuarios (nombre, usuario, password_hash, rol, activo) "
        "VALUES (%s, %s, %s, 'admin', TRUE)",
        (nombre, usuario, hash_password(password))
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    print(f"Usuario admin '{usuario}' creado correctamente.")


if __name__ == "__main__":
    nombre = input("Nombre completo: ").strip()
    usuario = input("Nombre de usuario (para iniciar sesión): ").strip()
    password = getpass.getpass("Contraseña: ")

    if not nombre or not usuario or not password:
        print("Todos los campos son obligatorios.")
    else:
        crear_admin(nombre, usuario, password)
