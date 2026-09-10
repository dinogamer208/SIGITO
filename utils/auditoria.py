"""
utils/auditoria.py
---------------------
Registro de auditoría (log) de todos los cambios importantes en la
base de datos: quién hizo qué, cuándo, y a qué artículo/asignación.
"""

from db.conexion import transaccion


def registrar_movimiento(articulo_id, tipo_movimiento, usuario_id=None,
                          asignacion_id=None, detalle=""):
    """
    Inserta una fila en historial_movimientos. Sirve como "caja negra":
    si algo raro pasa en la base de datos, este historial permite
    reconstruir la secuencia de eventos.
    """
    with transaccion() as (cursor, _con):
        cursor.execute("""
            INSERT INTO historial_movimientos
            (articulo_id, asignacion_id, tipo_movimiento, usuario_id, detalle)
            VALUES (%s, %s, %s, %s, %s)
        """, (articulo_id, asignacion_id, tipo_movimiento, usuario_id, detalle))


def listar_historial_por_articulo(articulo_id):
    """
    Devuelve todo el historial de un artículo específico, ordenado del
    más reciente al más antiguo.
    """
    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute("""
            SELECT * FROM historial_movimientos
            WHERE articulo_id = %s
            ORDER BY fecha DESC
        """, (articulo_id,))
        return cursor.fetchall()


def listar_historial_reciente(limite=10):
    """
    Últimos movimientos de todo el sistema (para el panel del dashboard),
    con el nombre de usuario resuelto vía JOIN cuando existe.
    """
    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute("""
            SELECT h.id, h.tipo_movimiento, h.fecha, h.detalle,
                   u.nombre AS usuario_nombre
            FROM historial_movimientos h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            ORDER BY h.fecha DESC
            LIMIT %s
        """, (limite,))
        return cursor.fetchall()
