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


def listar_historial(limite=300, tipo_movimiento=None, filtro_texto=None):
    """
    Historial completo del sistema para la pantalla de auditoría (a
    diferencia de listar_historial_reciente, que es solo para el panel
    resumido del dashboard). Incluye el código/nombre del artículo y el
    nombre de usuario, y admite filtrar por tipo de movimiento y/o texto
    libre (busca en el detalle, el artículo y el usuario).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    condiciones = []
    parametros = []

    if tipo_movimiento:
        condiciones.append("h.tipo_movimiento = %s")
        parametros.append(tipo_movimiento)

    if filtro_texto:
        condiciones.append(
            "(h.detalle LIKE %s OR ar.nombre LIKE %s OR ar.codigo_inventario LIKE %s "
            "OR u.nombre LIKE %s)"
        )
        comodin = f"%{filtro_texto}%"
        parametros += [comodin, comodin, comodin, comodin]

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    parametros.append(limite)

    cursor.execute(f"""
        SELECT h.id, h.tipo_movimiento, h.fecha, h.detalle,
               ar.codigo_inventario, ar.nombre AS articulo_nombre,
               u.nombre AS usuario_nombre
        FROM historial_movimientos h
        LEFT JOIN articulos ar ON ar.id = h.articulo_id
        LEFT JOIN usuarios u ON u.id = h.usuario_id
        {where}
        ORDER BY h.fecha DESC
        LIMIT %s
    """, tuple(parametros))

    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def listar_historial_reciente(limite=10):
    """
    Últimos movimientos de todo el sistema (para el panel del dashboard),
    con el nombre de usuario resuelto vía JOIN cuando existe.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT h.id, h.tipo_movimiento, h.fecha, h.detalle,
               u.nombre AS usuario_nombre
        FROM historial_movimientos h
        LEFT JOIN usuarios u ON u.id = h.usuario_id
        ORDER BY h.fecha DESC
        LIMIT %s
    """, (limite,))

    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas