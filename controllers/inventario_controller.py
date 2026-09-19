"""
controllers/inventario_controller.py — CRUD de artículos/categorías.

Responsable: Persona 3.

Qué debe hacer este archivo:
1. listar_articulos(filtro=None) -> devuelve lista de Articulo.
2. crear_articulo(...) -> INSERT en `articulos`, generando/validando
   el código de barras.
3. actualizar_estado_articulo(articulo_id, nuevo_estado) -> usado por
   asignacion_controller.py al prestar/devolver un artículo.
4. eliminar_articulo(articulo_id) / listar_categorias().

Recordatorio importante (aprendido en Café Nova): los ids que vienen
de widgets de Tkinter (ej. Treeview iid) llegan como string — convertir
siempre a int antes de usarlos en queries con FOREIGN KEY.

Esqueleto:
"""

from db.conexion import obtener_conexion
from models.articulo import Articulo
from utils.auditoria import registrar_movimiento


def generar_codigo_inventario(prefijo):
    """
    Busca el último código con ese prefijo y genera el siguiente.
    prefijo ejemplo: "TEC", "OFI"
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT codigo_inventario FROM articulos "
        "WHERE codigo_inventario LIKE %s "
        "ORDER BY id DESC LIMIT 1",
        (f"{prefijo}-%",)
    )
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()

    if resultado:
        ultimo_numero = int(resultado[0].split("-")[1])
        siguiente = ultimo_numero + 1
    else:
        siguiente = 1

    return f"{prefijo}-{siguiente:04d}" # TEC-0001, TEC-0002, etc.


# -----------------------------------------------------
# Agregar articulo nuevo
# -----------------------------------------------------
def agregar_articulo(datos):
    """
    datos: diccionario con las llaves:
    nombre, categoria_id, marca, modelo, serie, foto_path,
    estado_fisico, fecha_adquisicion, ubicacion_actual, prefijo_codigo,
    cantidad_total (opcional, default 1: cuántas unidades hay en stock
    de este artículo), codigo_manual (opcional: código de barras que el
    artículo ya trae de fábrica; si no se da, se genera uno nuevo con
    prefijo_codigo).

    Cada fila de `articulos` es un TIPO de artículo (ej. "Calculadora
    Casio"), no una unidad física: la cantidad se controla con
    cantidad_total/cantidad_disponible en vez de dar de alta una fila
    por cada unidad (eso era lento con cantidades grandes y obligaba a
    inventar códigos de barras con sufijo -2/-3... para cada copia).
    """

    codigo_manual = (datos.get("codigo_manual") or "").strip()
    cantidad_total = datos.get("cantidad_total") or 1

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if codigo_manual:
        cursor.execute(
            "SELECT id FROM articulos WHERE codigo_inventario = %s", (codigo_manual,)
        )
        if cursor.fetchone():
            cursor.close()
            conexion.close()
            raise ValueError(f"Ya existe un artículo con el código '{codigo_manual}'.")
        codigo_inventario = codigo_manual
    else:
        codigo_inventario = generar_codigo_inventario(datos["prefijo_codigo"])

    cursor.execute("""
        INSERT INTO articulos
        (codigo_inventario, nombre, categoria_id, marca, modelo, serie,
        foto_path, estado_fisico, estado_disponibilidad, cantidad_total,
        cantidad_disponible, fecha_adquisicion, ubicacion_actual)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'disponible', %s, %s, %s, %s)
    """, (
        codigo_inventario, datos["nombre"], datos["categoria_id"],
        datos.get("marca"), datos.get("modelo"), datos.get("serie"),
        datos.get("foto_path"), datos.get("estado_fisico", "bueno"),
        cantidad_total, cantidad_total,
        datos.get("fecha_adquisicion"), datos.get("ubicacion_actual")
    ))

    conexion.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conexion.close()
    # --- Registro de auditoría ---
    registrar_movimiento(
        articulo_id=nuevo_id,
        tipo_movimiento="alta",
        detalle=f"Artículo agregado: {codigo_inventario} - {datos['nombre']} (stock: {cantidad_total})"
    )

    return codigo_inventario, nuevo_id

# ---------------------------------------------------------
# Editar artículo existente
# ---------------------------------------------------------
def editar_articulo(id_articulo, datos):
    """
    Si `datos` trae "cantidad_total", ajusta también cantidad_disponible
    por la misma diferencia (ej. si el stock sube de 5 a 8, disponible
    también sube en 3; si baja, no se permite dejar cantidad_disponible
    en negativo -habría más unidades prestadas que stock nuevo-).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    campos_extra = ""
    valores_extra = []
    if "cantidad_total" in datos and datos["cantidad_total"] is not None:
        cursor.execute(
            "SELECT cantidad_total, cantidad_disponible FROM articulos WHERE id = %s",
            (id_articulo,)
        )
        fila = cursor.fetchone()
        if fila:
            total_anterior, disponible_anterior = fila
            nuevo_total = datos["cantidad_total"]
            nuevo_disponible = disponible_anterior + (nuevo_total - total_anterior)
            if nuevo_disponible < 0:
                cursor.close()
                conexion.close()
                prestadas = total_anterior - disponible_anterior
                raise ValueError(
                    f"No puedes bajar el stock a {nuevo_total}: hay {prestadas} "
                    "unidad(es) prestada(s) en este momento."
                )
            campos_extra = ", cantidad_total = %s, cantidad_disponible = %s"
            valores_extra = [nuevo_total, nuevo_disponible]

    cursor.execute(f"""
        UPDATE articulos SET
            nombre = %s, categoria_id = %s, marca = %s, modelo = %s,
            serie = %s, foto_path = %s, estado_fisico = %s,
            fecha_adquisicion = %s, ubicacion_actual = %s{campos_extra}
        WHERE id = %s
    """, (
        datos["nombre"], datos["categoria_id"], datos.get("marca"),
        datos.get("modelo"), datos.get("serie"), datos.get("foto_path"),
        datos.get("estado_fisico"), datos.get("fecha_adquisicion"),
        datos.get("ubicacion_actual"), *valores_extra, id_articulo
    ))

    conexion.commit()
    cursor.close()
    conexion.close()

# ---------------------------------------------------------
# Dar de baja un artículo (todo el stock deja de poder prestarse)
# ---------------------------------------------------------
def dar_de_baja(id_articulo):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE articulos SET estado_disponibilidad = 'de_baja', cantidad_disponible = 0 "
        "WHERE id = %s",
        (id_articulo,)
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    # --- Registro de auditoría ---
    registrar_movimiento(
        articulo_id=id_articulo,
        tipo_movimiento="baja",
        detalle=f"Artículo id={id_articulo} dado de baja"
    )

# ---------------------------------------------------------
# Buscar artículo por código (usado por el escáner)
# ---------------------------------------------------------
def buscar_articulo_por_codigo(codigo):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM articulos WHERE codigo_inventario = %s", (codigo,)
    )
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()

    if fila:
        return Articulo(**fila)
    return None

# ---------------------------------------------------------
# Listar artículos (con filtros opcionales)
# ---------------------------------------------------------
def listar_articulos(categoria_id=None, estado_disponibilidad=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    query = "SELECT * FROM articulos WHERE 1=1"
    params = []

    if categoria_id is not None:
        query += " AND categoria_id = %s"
        params.append(categoria_id)

    if estado_disponibilidad is not None:
        query += " AND estado_disponibilidad = %s"
        params.append(estado_disponibilidad)

    cursor.execute(query, tuple(params))
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

    return [Articulo(**fila) for fila in filas]

def generar_etiqueta(codigo_inventario, nombre_articulo, carpeta_salida="assets/etiquetas"):
    """
    Genera una imagen PNG con el código de barras + el nombre del artículo,
    lista para imprimir y pegar en el equipo físico.
    """
    # Imports locales: barcode/PIL son pesados (~100-260 ms) y solo se
    # necesitan aquí. Dejarlos a nivel de módulo hacía que abrir el
    # dashboard (que importa este controller) pagara ese costo siempre.
    import os

    import barcode
    from barcode.writer import ImageWriter
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(carpeta_salida, exist_ok=True)

    # 1. Generar el código de barras base (sin texto propio del código)
    codigo_barras = barcode.get('code128', codigo_inventario, writer=ImageWriter())
    ruta_barras_temp = os.path.join(carpeta_salida, f"{codigo_inventario}_temp")
    codigo_barras.save(ruta_barras_temp, options={"write_text": False})

    imagen_barras = Image.open(f"{ruta_barras_temp}.png")

    # 2. Crear una imagen nueva más grande, para poner el nombre arriba
    ancho = imagen_barras.width
    alto_extra = 40  # espacio para el texto del nombre
    imagen_final = Image.new("RGB", (ancho, imagen_barras.height + alto_extra), "white")

    # 3. Escribir el nombre del artículo en la parte superior
    dibujo = ImageDraw.Draw(imagen_final)
    try:
        fuente = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        fuente = ImageFont.load_default()  # si no encuentra arial, usa una fuente básica

    # Centrar el texto horizontalmente
    texto = nombre_articulo
    bbox = dibujo.textbbox((0, 0), texto, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    posicion_x = (ancho - ancho_texto) // 2
    dibujo.text((posicion_x, 10), texto, fill="black", font=fuente)

    # 4. Pegar el código de barras debajo del texto
    imagen_final.paste(imagen_barras, (0, alto_extra))

    # 5. Guardar la imagen final y borrar el archivo temporal
    ruta_final = os.path.join(carpeta_salida, f"{codigo_inventario}.png")
    imagen_final.save(ruta_final)
    os.remove(f"{ruta_barras_temp}.png")

    return ruta_final

# ---------------------------------------------------------
# CRUD de Categorías
# ---------------------------------------------------------

def agregar_categoria(nombre, descripcion=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
        (nombre, descripcion)
    )
    conexion.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conexion.close()
    return nuevo_id

def editar_categoria(id_categoria, nombre, descripcion=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE categorias SET nombre = %s, descripcion = %s WHERE id = %s",
        (nombre, descripcion, id_categoria)
    )
    conexion.commit()
    cursor.close()
    conexion.close()

def eliminar_categoria(id_categoria):
    """
    Antes de eliminar, verificar que no haya articulos usando esta
    categoria, para no dejar articulos huérfanos o romper la
    llave foránea.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM articulos WHERE categoria_id = %s",
        (id_categoria,)
    )
    cantidad = cursor.fetchone()[0]

    if cantidad > 0:
        cursor.close()
        conexion.close()
        raise ValueError(
            f"No se puede eliminar: hay {cantidad} artículo(s) usando esta categoría."
        )
    
    cursor.execute("DELETE FROM categorias WHERE id = %s", (id_categoria,))
    conexion.commit()
    cursor.close()
    conexion.close()

def listar_categorias():
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY nombre")
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return filas
