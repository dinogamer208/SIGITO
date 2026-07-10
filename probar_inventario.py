from controllers.inventario_controller import (
    agregar_articulo, listar_articulos, editar_articulo, dar_de_baja,
    buscar_articulo_por_codigo
)

# Primero necesitas al menos una categoría en la tabla `categorias`
# (puedes insertarla directo en la terminal MySQL):
# INSERT INTO categorias (nombre, descripcion) VALUES ('Cómputo', 'Equipo tecnológico');

datos_prueba = {
    "nombre": "Proyector Epson X200",
    "categoria_id": 1,
    "marca": "Epson",
    "modelo": "X200",
    "serie": "SN-12345",
    "estado_fisico": "bueno",
    "fecha_adquisicion": "2024-01-15",
    "ubicacion_actual": "Bodega Central",
    "prefijo_codigo": "TEC"
}

print("\n--- Probando editar_articulo ---")
datos_editados = {
    "nombre": "Proyector Epson X200 ()"
}

codigo, nuevo_id = agregar_articulo(datos_prueba)
print(f"Artículo creado: {codigo} (id={nuevo_id})")

articulos = listar_articulos()
for a in articulos:
    print(a)

print("\n--- Probando editar_articulo ---")
datos_editados = {
    "nombre": "Proyector Epson X200 (Editado)",
    "categoria_id": 1,
    "marca": "Epson",
    "modelo": "X200 Pro",
    "serie": "SN-12345",
    "estado_fisico": "regular",
    "fecha_adquisicion": "2024-01-15",
    "ubicacion_actual": "Aula 5"
}
editar_articulo(1, datos_editados)  # edita el artículo con id=1 (TEC-0001)
print("Artículo id=1 editado.")

articulos = listar_articulos()
for a in articulos:
    print(a, "-", a.estado_fisico, "-", a.ubicacion_actual)

print("\n--- Probando dar_de_baja ---")
dar_de_baja(2)  # da de baja el artículo con id=2 (TEC-0002)
print("Artículo id=2 dado de baja.")

articulos = listar_articulos()
for a in articulos:
    print(a, "-", a.estado_disponibilidad)

print("\n--- Probando buscar_articulo_por_codigo ---")

# Caso 1: código que SÏ existe
articulo = buscar_articulo_por_codigo("TEC-0001")
if articulo:
    print(f"Encontrado: {articulo} - {articulo.estado_disponibilidad} - {articulo.ubicacion_actual}")
else:
    print("No se encontró TEC-0001")
# Caso 2: código que NO existe (simula un escaneo de un código mal impreso o inválido)
articulo_falso = buscar_articulo_por_codigo("TEC-9999")
if articulo_falso:
    print(f"Encontrado: {articulo_falso}")
else:
    print("No se encontró TEC-9999 (como se esperaba)")

from controllers.inventario_controller import generar_etiqueta
print("\n--- Probando generar_etiqueta ---")
ruta = generar_etiqueta("TEC-0001", "Proyector Epson X200")
print(f"Etiqueta generada en: {ruta}")