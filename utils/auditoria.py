"""
utils/auditoria.py
---------------------
Registro de auditoría (log) de todos los cambios importantes en la
base de datos: quién hizo qué, cuándo, y a qué artículo/asignación.
"""

from db.conexion import obtener_conexion


def registrar_movimiento(articulo_id, tipo_movimiento, usuario_id=None,
                          asignacion_id=None, detalle=""):
    """
    Inserta una fila en historial_movimientos. Sirve como "caja negra":
    si algo raro pasa en la base de datos, este historial permite
    reconstruir la secuencia de eventos.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO historial_movimientos
        (articulo_id, asignacion_id, tipo_movimiento, usuario_id, detalle)
        VALUES (%s, %s, %s, %s, %s)
    """, (articulo_id, asignacion_id, tipo_movimiento, usuario_id, detalle))

    conexion.commit()
    cursor.close()
    conexion.close()


def listar_historial_por_articulo(articulo_id):
    """
    Devuelve todo el historial de un artículo específico, ordenado del
    más reciente al más antiguo.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM historial_movimientos
        WHERE articulo_id = %s
        ORDER BY fecha DESC
    """, (articulo_id,))

    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas