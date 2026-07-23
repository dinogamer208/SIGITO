"""
utils/exportador.py — Exportar reportes a PDF/Excel/CSV.

Responsable: Persona 5.

Qué debe hacer este archivo:
1. exportar_pdf(datos, ruta_salida) -> usando reportlab (o el skill de
   pdf si se genera desde un LLM, pero aquí es lógica pura de la app).
2. exportar_excel(datos, ruta_salida) -> usando openpyxl.
3. exportar_csv(datos, ruta_salida) -> csv de la librería estándar
   (no necesita dependencia extra).
4. `datos` debe ser una lista de dicts, tal como la devuelven las
   funciones de controllers/reportes_controller.py.

Esqueleto:
"""

import csv


def exportar_csv(datos: list[dict], ruta_salida: str) -> None:
    if not datos:
        raise ValueError("No hay datos para exportar")
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=datos[0].keys())
        writer.writeheader()
        writer.writerows(datos)


def exportar_excel(datos: list[dict], ruta_salida: str) -> None:
    if not datos:
        raise ValueError("No hay datos para exportar")

    from openpyxl import Workbook
    from openpyxl.styles import Font

    columnas = list(datos[0].keys())

    libro = Workbook()
    hoja = libro.active

    hoja.append(columnas)
    for celda in hoja[1]:
        celda.font = Font(bold=True)

    for fila in datos:
        hoja.append([str(fila.get(col, "")) for col in columnas])

    for i, columna in enumerate(columnas, start=1):
        ancho = max(len(columna), *(len(str(fila.get(columna, ""))) for fila in datos)) + 2
        hoja.column_dimensions[hoja.cell(row=1, column=i).column_letter].width = ancho

    libro.save(ruta_salida)


def exportar_pdf(datos: list[dict], ruta_salida: str) -> None:
    if not datos:
        raise ValueError("No hay datos para exportar")

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    columnas = list(datos[0].keys())
    filas = [[str(fila.get(col, "")) for col in columnas] for fila in datos]

    documento = SimpleDocTemplate(ruta_salida, pagesize=landscape(letter))
    tabla = Table([columnas] + filas, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    documento.build([tabla])
