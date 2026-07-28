"""
db/conexion.py — Conexión a MySQL.

Responsable: Persona 1.

Usa un pool de conexiones (mysql.connector.pooling) en vez de abrir una
conexión TCP + autenticación nueva en cada consulta: eso es lo que hacía
lenta la apertura del dashboard, que dispara varias consultas seguidas
apenas se muestra la ventana.

También expone cursor_db(), un context manager que reemplaza el bloque
repetido en cada función de los controllers:

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(...)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

por:

    with cursor_db(dictionary=True) as cursor:
        cursor.execute(...)
        filas = cursor.fetchall()

y además cierra el cursor/conexión aunque la consulta lance una excepción
(el patrón manual anterior dejaba la conexión abierta en ese caso).
"""

from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error, pooling
from config import DB_CONFIG

_pool = None


def _obtener_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="sigito_pool",
            pool_size=5,
            **DB_CONFIG
        )
    return _pool


def obtener_conexion():
    """
    Devuelve una conexión activa a MySQL, tomada del pool (o recién
    creada si el pool aún no llega a su tamaño máximo).
    Lanza una excepción si no logra conectar (para que quien la use
    decida qué hacer: mostrar error, o caer a modo offline).
    """
    try:
        return _obtener_pool().get_connection()
    except Error as e:
        print(f"[ERROR] No se pudo conectar a MySQL: {e}")
        raise


@contextmanager
def cursor_db(dictionary=False, commit=False):
    """
    Entrega un cursor listo para usar; al salir del bloque `with` cierra
    el cursor y devuelve la conexión al pool automáticamente (con commit
    si se pide). Si el bloque lanza una excepción, igual se cierra todo
    y la excepción sigue propagándose normalmente.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            conexion.commit()
    finally:
        cursor.close()
        conexion.close()


def hay_conexion_servidor(timeout=2):
    """
    Verifica rápidamente si el servidor está disponible,
    sin abrir una conexión completa de MySQL (más rápido).
    """
    import socket
    try:
        socket.create_connection((DB_CONFIG["host"], DB_CONFIG["port"]), timeout=timeout)
        return True
    except OSError:
        return False

def probar_conexion():
    """
    Función de prueba rápida: solo para verificar que todo esté bien
    configurado. Puedes correr este archivo para probar.
    """
    if hay_conexion_servidor():
        try:
            conexion = obtener_conexion()
            print("Conexión exitosa a MySQL")
            conexion.close()
        except Error as e:
            print(f"Error al conectar: {e}")
    else:
        print("No hay conexión al servidor (revisa host/puerto)")

if __name__ == "__main__":
    probar_conexion()