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

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

def obtener_conexion():
    """
    Devuelve una conexión activa a MySQL.
    Lanza una excepción si no logra conectar (para que quien la use
    decida qué hacer: mostrar error, o caer a modo offline).
    """
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        print(f"[ERROR] No se pudo conectar a MySQL: {e}")
        raise

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