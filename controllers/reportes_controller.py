"""
controllers/reportes_controller.py — Reportes/estadísticas.

Responsable: Persona 5.

Cada función devuelve una lista de dicts lista para mostrarse en un
Treeview o pasarse directo a utils/exportador.py.
"""

from db.conexion import obtener_conexion


def resumen_articulos_por_estado() -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT estado_disponibilidad AS estado, COUNT(*) AS cantidad
        FROM articulos
        GROUP BY estado_disponibilidad
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def prestamos_vencidos() -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.nombre_completo, a.seccion, a.anio, a.correo,
               ar.codigo_inventario, ar.nombre AS articulo_nombre,
               a.hora_salida, a.hora_estimada_devolucion
        FROM asignaciones a
        JOIN articulos ar ON ar.id = a.articulo_id
        WHERE a.hora_entrada_real IS NULL
          AND a.hora_estimada_devolucion < NOW()
        ORDER BY a.hora_estimada_devolucion ASC
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def articulos_por_categoria() -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.nombre AS categoria, COUNT(a.id) AS cantidad
        FROM categorias c
        LEFT JOIN articulos a ON a.categoria_id = c.id
        GROUP BY c.id, c.nombre
        ORDER BY cantidad DESC
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def asignaciones_por_mes(meses: int = 6) -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT DATE_FORMAT(hora_salida, '%Y-%m') AS mes, COUNT(*) AS cantidad
        FROM asignaciones
        WHERE hora_salida >= DATE_SUB(NOW(), INTERVAL %s MONTH)
        GROUP BY mes
        ORDER BY mes ASC
    """, (meses,))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def articulos_mas_prestados(limite: int = 10) -> list[dict]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT ar.codigo_inventario, ar.nombre, COUNT(a.id) AS veces_prestado
        FROM asignaciones a
        JOIN articulos ar ON ar.id = a.articulo_id
        GROUP BY ar.id, ar.codigo_inventario, ar.nombre
        ORDER BY veces_prestado DESC
        LIMIT %s
    """, (limite,))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas
