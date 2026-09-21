"""
controllers/mantenimiento_controller.py — Enviar equipo a mantenimiento
y registrar su regreso.

Solo el admin puede usar esto desde la UI (views/asignacion_view.py).
Una unidad en mantenimiento se resta de cantidad_disponible (igual que
un préstamo: no está disponible para prestarse mientras está fuera),
sin tocar cantidad_total ni estado_disponibilidad del artículo.
"""

from db.conexion import obtener_conexion
from models.mantenimiento import Mantenimiento
from utils.auditoria import registrar_movimiento


def enviar_a_mantenimiento(articulo_id: int, fecha, destino: str, causa: str,
                            fecha_retorno_estimada, tecnico: str = None,
                            costo: float = None, usuario_id: int = None) -> int:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute(
        "SELECT cantidad_disponible, nombre FROM articulos WHERE id = %s FOR UPDATE",
        (articulo_id,)
    )
    fila = cursor.fetchone()
    if not fila:
        cursor.close()
        conexion.close()
        raise ValueError(f"No existe el artículo id={articulo_id}")
    if fila["cantidad_disponible"] < 1:
        cursor.close()
        conexion.close()
        raise ValueError("No hay unidades disponibles de este artículo para enviar a mantenimiento.")

    cursor.execute(
        "UPDATE articulos SET cantidad_disponible = cantidad_disponible - 1 WHERE id = %s",
        (articulo_id,)
    )

    cursor.execute("""
        INSERT INTO mantenimientos
        (articulo_id, fecha, descripcion, destino, fecha_retorno_estimada, estado, costo, tecnico)
        VALUES (%s, %s, %s, %s, %s, 'en_mantenimiento', %s, %s)
    """, (articulo_id, fecha, causa, destino, fecha_retorno_estimada, costo, tecnico))

    conexion.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conexion.close()

    registrar_movimiento(
        articulo_id=articulo_id, tipo_movimiento="mantenimiento", usuario_id=usuario_id,
        detalle=f"Enviado a mantenimiento a «{destino}»: {causa} "
                f"(regreso estimado: {fecha_retorno_estimada})"
    )

    return nuevo_id


def marcar_regresado(mantenimiento_id: int, usuario_id: int = None) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT * FROM mantenimientos WHERE id = %s", (mantenimiento_id,))
    fila = cursor.fetchone()
    if not fila:
        cursor.close()
        conexion.close()
        raise ValueError(f"No existe el mantenimiento id={mantenimiento_id}")
    if fila["estado"] == "regresado":
        cursor.close()
        conexion.close()
        raise ValueError("Este mantenimiento ya fue marcado como regresado.")

    cursor.execute(
        "UPDATE mantenimientos SET estado = 'regresado' WHERE id = %s",
        (mantenimiento_id,)
    )
    cursor.execute(
        "UPDATE articulos SET cantidad_disponible = LEAST(cantidad_total, cantidad_disponible + 1) "
        "WHERE id = %s",
        (fila["articulo_id"],)
    )
    conexion.commit()
    cursor.close()
    conexion.close()

    registrar_movimiento(
        articulo_id=fila["articulo_id"], tipo_movimiento="mantenimiento", usuario_id=usuario_id,
        detalle=f"Regresó de mantenimiento (enviado a «{fila['destino']}»)"
    )


def listar_en_mantenimiento() -> list[dict]:
    """Mantenimientos activos (todavía no regresados), con el nombre y
    código del artículo, para mostrarlos en Asignaciones."""
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.id, m.fecha, m.descripcion, m.destino, m.fecha_retorno_estimada,
               m.tecnico, m.costo, ar.codigo_inventario, ar.nombre AS articulo_nombre
        FROM mantenimientos m
        JOIN articulos ar ON ar.id = m.articulo_id
        WHERE m.estado = 'en_mantenimiento'
        ORDER BY m.fecha_retorno_estimada ASC
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas
