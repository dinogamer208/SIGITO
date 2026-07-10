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
    # TODO: usar openpyxl.Workbook(), escribir encabezados y filas
    raise NotImplementedError


def exportar_pdf(datos: list[dict], ruta_salida: str) -> None:
    # TODO: usar reportlab.platypus para armar una tabla simple
    raise NotImplementedError
