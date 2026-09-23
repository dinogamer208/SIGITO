"""
controllers/reportes_controller.py — Reportes/estadísticas.

Responsable: Persona 5.

Cada función devuelve una lista de dicts lista para mostrarse en un
Treeview o pasarse directo a utils/exportador.py.
"""

from db.conexion import obtener_conexion


def resumen_articulos_por_estado() -> list[dict]:
    """
    Cada fila de `articulos` es un tipo de artículo con cantidad_total/
    cantidad_disponible (no una unidad física), así que "disponible" y
    "prestado" ahora sirven de unidades en stock, no de filas contadas.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            SUM(CASE WHEN estado_disponibilidad = 'disponible' THEN cantidad_disponible ELSE 0 END) AS disponible,
            SUM(CASE WHEN estado_disponibilidad = 'disponible' THEN cantidad_total - cantidad_disponible ELSE 0 END) AS prestado,
            SUM(CASE WHEN estado_disponibilidad = 'de_baja' THEN cantidad_total ELSE 0 END) AS de_baja
        FROM articulos
    """)
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()

    return [
        {"estado": estado, "cantidad": int(fila.get(estado) or 0)}
        for estado in ("disponible", "prestado", "de_baja")
    ]


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


# Filtro de fecha (sobre hora_salida) para cada periodo del ranking.
_FILTROS_PERIODO = {
    "dia":  "DATE(a.hora_salida) = CURDATE()",
    "mes":  "YEAR(a.hora_salida) = YEAR(CURDATE()) AND MONTH(a.hora_salida) = MONTH(CURDATE())",
    "anio": "YEAR(a.hora_salida) = YEAR(CURDATE())",
    None:   "TRUE",
}


def articulos_mas_prestados(limite: int = 10, periodo: str = None) -> list[dict]:
    """
    Ranking de artículos por número de préstamos. `periodo` limita a los
    préstamos de hoy ("dia"), del mes actual ("mes"), del año actual
    ("anio") o de siempre (None). `unidades` suma la cantidad de cada
    préstamo (un préstamo puede llevarse varias unidades).
    """
    filtro = _FILTROS_PERIODO[periodo]
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT ar.codigo_inventario, ar.nombre, c.nombre AS categoria,
               COUNT(a.id) AS veces_prestado, SUM(a.cantidad) AS unidades
        FROM asignaciones a
        JOIN articulos ar ON ar.id = a.articulo_id
        LEFT JOIN categorias c ON c.id = ar.categoria_id
        WHERE {filtro}
        GROUP BY ar.id, ar.codigo_inventario, ar.nombre, c.nombre
        ORDER BY veces_prestado DESC, unidades DESC
        LIMIT %s
    """, (limite,))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas
