"""
controllers/asignacion_controller.py — Lógica de préstamos/devoluciones.

Responsable: Persona 4.
"""

from datetime import datetime

from db.conexion import obtener_conexion
from models.asignacion import Asignacion
from utils.auditoria import registrar_movimiento


def registrar_prestamo(articulo_id: int, nombre_completo: str, seccion: str,
                        anio: str, telefono: str, correo: str,
                        profesor_autoriza_id: int, hora_estimada_devolucion,
                        usuario_registro_id: int, foto_alumno: str = None,
                        cantidad: int = 1) -> int:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    # Todo o nada: si algo falla (incluidas las validaciones, que ocurren
    # con la fila del artículo bloqueada por FOR UPDATE), deshacer para no
    # dejar el stock descontado ni el artículo bloqueado.
    try:
        cursor.execute(
            "SELECT estado_disponibilidad, cantidad_disponible FROM articulos "
            "WHERE id = %s FOR UPDATE",
            (articulo_id,)
        )
        fila = cursor.fetchone()
        if not fila:
            raise ValueError(f"No existe el artículo id={articulo_id}")
        if fila["estado_disponibilidad"] != "disponible":
            raise ValueError("El artículo no está disponible para préstamo.")
        if fila["cantidad_disponible"] < cantidad:
            raise ValueError(
                f"Solo hay {fila['cantidad_disponible']} unidad(es) disponible(s) de este artículo."
            )

        cursor.execute(
            "UPDATE articulos SET cantidad_disponible = cantidad_disponible - %s WHERE id = %s",
            (cantidad, articulo_id)
        )

        cursor.execute("""
            INSERT INTO asignaciones
            (articulo_id, cantidad, nombre_completo, seccion, anio, telefono, correo,
             foto_alumno, profesor_autoriza_id, hora_salida,
             hora_estimada_devolucion, estado, usuario_registro_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, 'en_uso', %s)
        """, (
            articulo_id, cantidad, nombre_completo, seccion, anio, telefono, correo,
            foto_alumno, profesor_autoriza_id, hora_estimada_devolucion, usuario_registro_id
        ))
        conexion.commit()
        nueva_id = cursor.lastrowid
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    registrar_movimiento(
        articulo_id=articulo_id,
        tipo_movimiento="prestamo",
        usuario_id=usuario_registro_id,
        asignacion_id=nueva_id,
        detalle=f"Préstamo de {cantidad} unidad(es) a {nombre_completo} ({seccion} {anio})"
    )

    return nueva_id


def registrar_devolucion(asignacion_id: int, usuario_devolucion_id: int,
                         danado: bool = False, observaciones: str = None,
                         foto_devolucion: str = None, cantidad_devuelta: int = None) -> None:
    """
    Registra la devolución. Si `danado` es True, el profesor indicó que
    el equipo regresó dañado: se guarda en la asignación (con la
    descripción en `observaciones` y la foto del daño en
    `foto_devolucion`) y el artículo queda con
    estado_fisico = 'dañado' para que se vea en el inventario.

    `cantidad_devuelta` permite una devolución PARCIAL (ej. se llevó 3 y
    devuelve 2): la asignación original sigue activa con las unidades que
    faltan, y lo devuelto queda como una asignación aparte ya cerrada
    (con su condición/daño), para que el historial conserve ambas partes.
    """
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

    articulo_id = fila["articulo_id"]
    total = fila["cantidad"]
    devueltas = total if cantidad_devuelta is None else int(cantidad_devuelta)
    if not 1 <= devueltas <= total:
        cursor.close()
        conexion.close()
        raise ValueError(f"La cantidad devuelta debe estar entre 1 y {total}.")
    parcial = devueltas < total

    # Todo o nada: si algo falla, deshacer para no dejar la transacción
    # abierta (bloquearía las tablas) ni una devolución a medias.
    try:
        if parcial:
            # Lo que falta sigue prestado en la asignación original...
            cursor.execute(
                "UPDATE asignaciones SET cantidad = cantidad - %s WHERE id = %s",
                (devueltas, asignacion_id)
            )
            # ...y lo devuelto queda como una asignación aparte, ya cerrada.
            cursor.execute("""
                INSERT INTO asignaciones
                (articulo_id, cantidad, nombre_completo, seccion, anio, telefono, correo,
                 foto_alumno, profesor_autoriza_id, hora_salida, hora_estimada_devolucion,
                 hora_entrada_real, estado, correo_aviso_enviado, usuario_registro_id,
                 usuario_devolucion_id, devuelto_danado, observaciones_devolucion, foto_devolucion)
                SELECT articulo_id, %s, nombre_completo, seccion, anio, telefono, correo,
                       foto_alumno, profesor_autoriza_id, hora_salida, hora_estimada_devolucion,
                       NOW(), 'devuelto', correo_aviso_enviado, usuario_registro_id,
                       %s, %s, %s, %s
                FROM asignaciones WHERE id = %s
            """, (devueltas, usuario_devolucion_id, danado, observaciones or None,
                  foto_devolucion, asignacion_id))
        else:
            cursor.execute("""
                UPDATE asignaciones
                SET hora_entrada_real = NOW(), estado = 'devuelto',
                    usuario_devolucion_id = %s,
                    devuelto_danado = %s, observaciones_devolucion = %s,
                    foto_devolucion = %s
                WHERE id = %s
            """, (usuario_devolucion_id, danado, observaciones or None,
                  foto_devolucion, asignacion_id))

        cursor.execute(
            "UPDATE articulos SET cantidad_disponible = LEAST(cantidad_total, cantidad_disponible + %s) "
            "WHERE id = %s",
            (devueltas, articulo_id)
        )
        if danado:
            cursor.execute(
                "UPDATE articulos SET estado_fisico = 'dañado' WHERE id = %s",
                (articulo_id,)
            )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    if parcial:
        detalle = (f"Devolución parcial de {devueltas} de {total} unidad(es) registrada para "
                   f"{fila['nombre_completo']} (quedan {total - devueltas} pendientes)")
    else:
        detalle = f"Devolución de {total} unidad(es) registrada para {fila['nombre_completo']}"
    if danado:
        detalle += " — REGRESÓ DAÑADO"
        if observaciones:
            detalle += f": {observaciones}"

    registrar_movimiento(
        articulo_id=articulo_id,
        tipo_movimiento="devolucion",
        usuario_id=usuario_devolucion_id,
        asignacion_id=asignacion_id,
        detalle=detalle
    )


def extender_prestamo(asignacion_id: int, nueva_fecha, usuario_id: int = None) -> None:
    """
    Cambia la fecha/hora estimada de devolución de un préstamo activo.
    Si la nueva fecha es futura, vuelve a 'en_uso' y reactiva el aviso de
    atraso (para que se avise otra vez si vuelve a vencer).
    """
    if isinstance(nueva_fecha, str):
        nueva_fecha = datetime.strptime(nueva_fecha, "%Y-%m-%d %H:%M")
    if nueva_fecha <= datetime.now():
        raise ValueError("La nueva fecha de devolución debe ser posterior a este momento.")

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM asignaciones WHERE id = %s", (asignacion_id,))
        fila = cursor.fetchone()
        if not fila:
            raise ValueError(f"No existe la asignación id={asignacion_id}")
        if fila["hora_entrada_real"] is not None:
            raise ValueError("Este préstamo ya fue devuelto.")
        cursor.execute("""
            UPDATE asignaciones
            SET hora_estimada_devolucion = %s, estado = 'en_uso', correo_aviso_enviado = FALSE
            WHERE id = %s
        """, (nueva_fecha, asignacion_id))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    registrar_movimiento(
        articulo_id=fila["articulo_id"],
        tipo_movimiento="prestamo",
        usuario_id=usuario_id,
        asignacion_id=asignacion_id,
        detalle=(f"Plazo extendido para {fila['nombre_completo']}: "
                 f"{fila['hora_estimada_devolucion']:%Y-%m-%d %H:%M} → {nueva_fecha:%Y-%m-%d %H:%M}")
    )


def historial_prestamos_alumno(nombre: str) -> list[dict]:
    """Todos los préstamos de un alumno (activos y devueltos), del más
    reciente al más antiguo, con su artículo, condición y si fue tarde."""
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.nombre_completo, a.cantidad, a.hora_salida, a.hora_estimada_devolucion,
               a.hora_entrada_real, a.devuelto_danado, a.observaciones_devolucion,
               a.foto_devolucion, a.foto_alumno,
               art.nombre AS articulo_nombre, art.codigo_inventario,
               (a.hora_entrada_real > a.hora_estimada_devolucion
                OR (a.hora_entrada_real IS NULL AND a.hora_estimada_devolucion < NOW())) AS tarde
        FROM asignaciones a
        JOIN articulos art ON art.id = a.articulo_id
        ORDER BY a.hora_salida DESC, a.id DESC
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    clave = clave_alumno(nombre)
    return [f for f in filas if clave_alumno(f["nombre_completo"]) == clave]


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


_CAMPOS_PRESTAMO_ACTIVO = """
    SELECT a.id, a.nombre_completo, a.seccion, a.anio, a.cantidad,
           a.hora_salida, a.hora_estimada_devolucion,
           (a.hora_estimada_devolucion < NOW()) AS vencido,
           art.id AS articulo_id, art.nombre AS articulo_nombre, art.codigo_inventario
    FROM asignaciones a
    JOIN articulos art ON art.id = a.articulo_id
"""


def prestamos_activos_de_articulo(articulo_id: int) -> list[dict]:
    """Préstamos sin devolver de un artículo (para "devolver escaneando":
    un mismo artículo con stock puede estar prestado a varios alumnos).
    Los vencidos primero, luego el más antiguo."""
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(_CAMPOS_PRESTAMO_ACTIVO + """
        WHERE a.articulo_id = %s AND a.hora_entrada_real IS NULL
        ORDER BY vencido DESC, a.hora_salida ASC
    """, (articulo_id,))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def detalle_prestamo(asignacion_id: int):
    """Alumno + artículo de un préstamo (dict), o None si no existe."""
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(_CAMPOS_PRESTAMO_ACTIVO + " WHERE a.id = %s", (asignacion_id,))
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()
    return fila


def listar_devoluciones(limite: int = 30) -> list[dict]:
    """
    Historial de devoluciones ya registradas, con el nombre de quién
    recibió cada equipo (usuario_devolucion_id) para poder mostrar en
    pantalla quién ha devuelto cada préstamo.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.nombre_completo, a.seccion, a.anio,
               a.hora_salida, a.hora_entrada_real,
               a.devuelto_danado, a.observaciones_devolucion, a.foto_devolucion,
               art.nombre AS articulo_nombre, art.codigo_inventario,
               u.nombre AS devuelto_por
        FROM asignaciones a
        JOIN articulos art ON art.id = a.articulo_id
        LEFT JOIN usuarios u ON u.id = a.usuario_devolucion_id
        WHERE a.hora_entrada_real IS NOT NULL
        ORDER BY a.hora_entrada_real DESC
        LIMIT %s
    """, (limite,))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


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


def listar_vencidas_sin_aviso() -> list[dict]:
    """
    Préstamos vencidos a los que todavía no se les avisó (correo/toast) de
    su atraso. Usado por utils/monitor.py cada 5 minutos: llamar primero a
    listar_vencidas() para que el estado 'atrasado' esté al día.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.nombre_completo, a.seccion, a.anio, a.correo,
               ar.codigo_inventario, ar.nombre AS articulo_nombre,
               a.hora_estimada_devolucion
        FROM asignaciones a
        JOIN articulos ar ON ar.id = a.articulo_id
        WHERE a.hora_entrada_real IS NULL
          AND a.hora_estimada_devolucion < NOW()
          AND a.correo_aviso_enviado = FALSE
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas


def marcar_aviso_enviado(asignacion_id: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE asignaciones SET correo_aviso_enviado = TRUE WHERE id = %s",
        (asignacion_id,)
    )
    conexion.commit()
    cursor.close()
    conexion.close()


# ------------------------------------------------------------
# Marcas de comportamiento del alumno
# ------------------------------------------------------------
# El alumno no tiene tabla propia (sus datos van en cada asignación), así
# que se le identifica por su nombre completo, sin importar mayúsculas,
# acentos ni espacios de más.
DANOS_PARA_NO_CUIDA = 3
TARDANZAS_PARA_TARDISTA = 10

MARCA_NO_CUIDA = "No cuida"
MARCA_TARDISTA = "Tardista"
MARCA_AMBAS = "No cuida y tardista"


def clave_alumno(nombre: str) -> str:
    import unicodedata
    sin_acentos = unicodedata.normalize("NFKD", nombre or "")
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.casefold().split())


def _marca(danos: int, tardanzas: int):
    no_cuida = danos >= DANOS_PARA_NO_CUIDA
    tardista = tardanzas >= TARDANZAS_PARA_TARDISTA
    if no_cuida and tardista:
        return MARCA_AMBAS
    if no_cuida:
        return MARCA_NO_CUIDA
    if tardista:
        return MARCA_TARDISTA
    return None


def historial_alumnos() -> dict[str, dict]:
    """
    Por alumno (clave_alumno(nombre) -> dict): cuántas veces devolvió
    equipo dañado, cuántas veces llegó tarde y su marca (o None).
    Cuenta como tardanza una devolución registrada después de la hora
    estimada, y también un préstamo que sigue sin devolverse y ya venció.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT nombre_completo, seccion, anio, telefono, correo, devuelto_danado,
               (hora_entrada_real > hora_estimada_devolucion
                OR (hora_entrada_real IS NULL AND hora_estimada_devolucion < NOW())) AS tarde
        FROM asignaciones
        ORDER BY hora_salida ASC
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

    resultado = {}
    for fila in filas:
        datos = resultado.setdefault(
            clave_alumno(fila["nombre_completo"]),
            {"nombre": fila["nombre_completo"], "danos": 0, "tardanzas": 0}
        )
        # Filas en orden cronológico: se quedan el nombre (tal como se
        # escribió), sección, año, teléfono y correo del préstamo más reciente.
        datos.update(nombre=fila["nombre_completo"], seccion=fila["seccion"], anio=fila["anio"],
                     telefono=fila["telefono"], correo=fila["correo"])
        datos["danos"] += 1 if fila["devuelto_danado"] else 0
        datos["tardanzas"] += 1 if fila["tarde"] else 0

    for datos in resultado.values():
        datos["marca"] = _marca(datos["danos"], datos["tardanzas"])
    return resultado


def alumnos_marcados() -> list[dict]:
    """Solo los alumnos con alguna marca; primero los que tienen ambas,
    luego por número de incidencias."""
    orden = {MARCA_AMBAS: 0, MARCA_NO_CUIDA: 1, MARCA_TARDISTA: 2}
    marcados = [d for d in historial_alumnos().values() if d["marca"]]
    return sorted(marcados, key=lambda d: (orden[d["marca"]], -(d["danos"] + d["tardanzas"])))


def buscar_alumnos(texto: str, limite: int = 6, historial: dict = None) -> list[dict]:
    """
    Alumnos que ya han pedido préstamos y cuyo nombre contiene `texto`
    (sin importar mayúsculas ni acentos), con sus datos más recientes y su
    historial/marca. Primero los que empiezan con el texto. Para el
    autocompletado del formulario de nuevo préstamo; `historial` permite
    pasar un historial_alumnos() ya cargado para no consultar la BD en
    cada tecla.
    """
    buscado = clave_alumno(texto)
    if not buscado:
        return []
    coincidencias = [
        (clave, datos) for clave, datos in (historial or historial_alumnos()).items()
        if buscado in clave
    ]
    coincidencias.sort(key=lambda par: (not par[0].startswith(buscado), par[0]))
    return [datos for _, datos in coincidencias[:limite]]


def historial_alumno(nombre: str) -> dict:
    """Igual que historial_alumnos(), pero de un solo alumno."""
    return historial_alumnos().get(
        clave_alumno(nombre),
        {"nombre": nombre, "danos": 0, "tardanzas": 0, "marca": None}
    )
