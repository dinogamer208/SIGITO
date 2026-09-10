"""
db/conexion.py — Conexión a MySQL.

Responsable: Persona 1.

Qué debe hacer este archivo:
1. Exponer una función obtener_conexion() que devuelva una conexión
   mysql.connector lista para usar (usando config.py).
2. Idealmente usar un pool de conexiones (mysql.connector.pooling) para
   que controllers/ no abran una conexión nueva en cada consulta.
3. Manejar el error de "Access denied" / "Can't connect" mostrando un
   mensaje claro (recordar: el usuario de MySQL debe tener permiso
   sobre el host correcto, ej. 'sigito_app'@'192.168.56.%').

Esqueleto:
"""

import threading
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error, pooling
from config import DB_CONFIG

_pool = None
_pool_lock = threading.Lock()


def _obtener_pool():
    """
    Crea el pool de conexiones la primera vez que se necesita (no al
    importar el módulo, para no intentar conectar antes de que main.py
    valide que el servidor está disponible). main.py la precalienta en
    un hilo aparte, así que el lock evita crear el pool dos veces si el
    hilo de precalentado y el login caen al mismo tiempo.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pooling.MySQLConnectionPool(
                    pool_name="sigito_pool",
                    pool_size=3,
                    **DB_CONFIG
                )
    return _pool


def obtener_conexion():
    """
    Devuelve una conexión del pool, lista para usar. Cada obtener_conexion()
    ya no abre un handshake TCP+auth nuevo: reutiliza una de las conexiones
    del pool (conexion.close() la libera de vuelta al pool en vez de cerrarla).
    Lanza una excepción si no logra conectar (para que quien la use
    decida qué hacer: mostrar error, o caer a modo offline).
    """
    try:
        return _obtener_pool().get_connection()
    except Error as e:
        print(f"[ERROR] No se pudo conectar a MySQL: {e}")
        raise

@contextmanager
def transaccion(dictionary=False):
    """
    Context manager para una operación de base de datos. Entrega
    ``(cursor, conexion)``, hace ``commit()`` si el bloque termina bien,
    ``rollback()`` si lanza una excepción, y SIEMPRE cierra el cursor y
    devuelve la conexión al pool.

    Antes cada función hacía ``cursor.close(); conexion.close()`` como
    sentencias sueltas: si ``cursor.execute`` fallaba, la conexión nunca
    volvía al pool y, con ``pool_size=3``, tres errores dejaban la app
    colgada para siempre en ``get_connection()``.

        with transaccion(dictionary=True) as (cur, con):
            cur.execute("SELECT ...", params)
            filas = cur.fetchall()

    Las funciones de solo lectura también pueden usarlo: el ``commit()``
    sobre un SELECT no tiene efecto.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=dictionary)
    try:
        yield cursor, conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
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