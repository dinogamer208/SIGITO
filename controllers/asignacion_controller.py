"""
controllers/asignacion_controller.py — Lógica de préstamos/devoluciones.

Responsable: Persona 4.
"""

from datetime import datetime

from db.conexion import obtener_conexion
from models.asignacion import Asignacion
from controllers.inventario_controller import actualizar_estado_articulo
from utils.auditoria import registrar_movimiento


def registrar_prestamo(articulo_id: int, nombre_completo: str, seccion: str,
                        anio: str, telefono: str, correo: str,
                        profesor_autoriza_id: int, hora_estimada_devolucion,
                        usuario_registro_id: int) -> int:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute(
        "SELECT estado_disponibilidad FROM articulos WHERE id = %s FOR UPDATE",
        (articulo_id,)
    )
    fila = cursor.fetchone()
    if not fila:
        cursor.close()
        conexion.close()
        raise ValueError(f"No existe el artículo id={articulo_id}")
    if fila["estado_disponibilidad"] != "disponible":
        cursor.close()
        conexion.close()
        raise ValueError("El artículo no está disponible para préstamo.")

    cursor.execute("""
        INSERT INTO asignaciones
        (articulo_id, nombre_completo, seccion, anio, telefono, correo,
         profesor_autoriza_id, hora_salida, hora_estimada_devolucion,
         estado, usuario_registro_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, 'en_uso', %s)
    """, (
        articulo_id, nombre_completo, seccion, anio, telefono, correo,
        profesor_autoriza_id, hora_estimada_devolucion, usuario_registro_id
    ))
    conexion.commit()
    nueva_id = cursor.lastrowid
    cursor.close()
    conexion.close()

    actualizar_estado_articulo(articulo_id, "prestado")
    registrar_movimiento(
        articulo_id=articulo_id,
        tipo_movimiento="prestamo",
        usuario_id=usuario_registro_id,
        asignacion_id=nueva_id,
        detalle=f"Préstamo a {nombre_completo} ({seccion} {anio})"
    )

    return nueva_id


def registrar_devolucion(asignacion_id: int, usuario_devolucion_id: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT * FROM asignaciones WHERE id = %s", (asignacion_id,))
    fila = cursor.fetchone()
    if not fila:
        cursor.close()
        conexion.close()
        raise ValueError(f"No existe la asignación id={asignacion_id}")
    if fila["hora_entrada_real"] is not None:
        cursor.close()
        conexion.close()
        raise ValueError("Esta asignación ya fue devuelta.")

    cursor.execute("""
        UPDATE asignaciones
        SET hora_entrada_real = NOW(), estado = 'devuelto',
            usuario_devolucion_id = %s
        WHERE id = %s
    """, (usuario_devolucion_id, asignacion_id))
    conexion.commit()
    cursor.close()
    conexion.close()

    articulo_id = fila["articulo_id"]
    actualizar_estado_articulo(articulo_id, "disponible")
    registrar_movimiento(
        articulo_id=articulo_id,
        tipo_movimiento="devolucion",
        usuario_id=usuario_devolucion_id,
        asignacion_id=asignacion_id,
        detalle=f"Devolución registrada para {fila['nombre_completo']}"
    )


def listar_asignaciones_activas() -> list[Asignacion]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM asignaciones WHERE hora_entrada_real IS NULL "
        "ORDER BY hora_salida DESC"
    )
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [Asignacion.desde_fila(fila) for fila in filas]


def listar_vencidas() -> list[Asignacion]:
    """
    Asignaciones activas cuya hora estimada de devolución ya pasó.
    De paso, marca su estado como 'atrasado' en la BD (sin monitor de
    correo automático en esta fase, esto solo mantiene el estado
    consistente para reportes/dashboard).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE asignaciones SET estado = 'atrasado'
        WHERE hora_entrada_real IS NULL
          AND hora_estimada_devolucion < NOW()
          AND estado != 'atrasado'
    """)
    conexion.commit()
    cursor.close()
    conexion.close()

    return [a for a in listar_asignaciones_activas() if a.esta_vencida()]
