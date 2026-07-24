"""
views/componentes.py
----------------------
Widgets reutilizables para las ventanas internas del Dashboard
(Inventario, Asignaciones, Reportes, Usuarios), siguiendo el mismo
lenguaje visual de dashboard_view.py (tarjetas redondeadas, franja de
color superior en los KPI, badges de estado) y el layout de referencia
de los mockups de Stitch (KPI cards con acento de color + tabla
principal con badges y columna de acciones).

Todas las vistas internas importan de aquí en vez de reconstruir
tarjetas/badges a mano, igual que todas importan colores desde tema.py.
"""

import customtkinter as ctk


def crear_kpi_card(padre, colores, numero, titulo, color_acento):
    """
    Tarjeta KPI con franja de color superior (patrón usado en todas las
    pantallas de los mockups de Stitch: Total, Prestados, Vencidos, etc.)
    """
    contenedor = ctk.CTkFrame(padre, fg_color="transparent")

    ctk.CTkFrame(contenedor, height=3, fg_color=color_acento,
                 corner_radius=0).pack(fill="x")

    cuerpo = ctk.CTkFrame(
        contenedor,
        fg_color=colores["card"],
        corner_radius=14,
        border_width=1,
        border_color=colores["borde"],
    )
    cuerpo.pack(fill="both", expand=True)

    ctk.CTkLabel(
        cuerpo, text=titulo.upper(),
        font=("Segoe UI", 11, "bold"),
        text_color=colores["subtext"]
    ).pack(anchor="w", padx=16, pady=(14, 0))

    ctk.CTkLabel(
        cuerpo, text=str(numero),
        font=("Segoe UI", 26, "bold"),
        text_color=colores["texto"]
    ).pack(anchor="w", padx=16, pady=(2, 14))

    return contenedor


def crear_badge(padre, texto, fondo, texto_color):
    """Chip redondeado para estados (Disponible, Prestado, Vencido...)."""
    return ctk.CTkLabel(
        padre, text=f"  {texto}  ",
        font=("Segoe UI", 10, "bold"),
        fg_color=fondo, text_color=texto_color,
        corner_radius=10,
    )


def crear_card(padre, colores, **kwargs):
    """Tarjeta base (fondo, borde y radio consistentes con el dashboard)."""
    opciones = dict(
        fg_color=colores["card"],
        corner_radius=16,
        border_width=1,
        border_color=colores["borde"],
    )
    opciones.update(kwargs)
    return ctk.CTkFrame(padre, **opciones)


def crear_encabezado(padre, colores, titulo, subtitulo):
    """Título + subtítulo estándar de cada pantalla interna."""
    contenedor = ctk.CTkFrame(padre, fg_color="transparent")

    ctk.CTkLabel(
        contenedor, text=titulo,
        font=("Segoe UI", 22, "bold"),
        text_color=colores["texto"]
    ).pack(anchor="w")

    ctk.CTkLabel(
        contenedor, text=subtitulo,
        font=("Segoe UI", 12),
        text_color=colores["subtext"]
    ).pack(anchor="w", pady=(2, 0))

    return contenedor


def crear_fila_tabla(padre, colores, celdas, ancho_columnas, acciones=None):
    """
    Fila de tabla estilo "card" (misma paleta que dash_fila). `celdas` es
    una lista de textos simples; para una celda con contenido custom
    (ej. avatar + nombre) pasa una función `fn(celda_frame)` en su lugar.
    `acciones` es una lista opcional de (texto, comando) mostrados a la
    derecha (ej. [("Editar", cb), ("Baja", cb)]).
    """
    fila = ctk.CTkFrame(padre, fg_color=colores["fila"], corner_radius=10, height=52)
    fila.pack(fill="x", pady=3, padx=2)
    fila.pack_propagate(False)

    for contenido, ancho in zip(celdas, ancho_columnas):
        celda = ctk.CTkFrame(fila, fg_color="transparent", width=ancho)
        celda.pack(side="left", fill="y", padx=(12, 0))
        celda.pack_propagate(False)

        if callable(contenido):
            contenido(celda)
        else:
            ctk.CTkLabel(
                celda, text=str(contenido), anchor="w",
                font=("Segoe UI", 12),
                text_color=colores["texto"]
            ).place(relx=0, rely=0.5, anchor="w")

    if acciones:
        for texto, comando in reversed(acciones):
            ctk.CTkButton(
                fila, text=texto, width=54, height=26,
                corner_radius=8, font=("Segoe UI", 11, "bold"),
                fg_color="transparent", text_color=colores["link"],
                hover_color=colores["card_inner"],
                command=comando
            ).pack(side="right", padx=(0, 6))

    return fila


def crear_encabezado_tabla(padre, colores, titulos, ancho_columnas):
    """Fila de encabezados (mayúsculas, gris) para una tabla tipo card."""
    fila = ctk.CTkFrame(padre, fg_color="transparent", height=28)
    fila.pack(fill="x", padx=2, pady=(0, 4))
    fila.pack_propagate(False)

    for titulo, ancho in zip(titulos, ancho_columnas):
        celda = ctk.CTkFrame(fila, fg_color="transparent", width=ancho)
        celda.pack(side="left", fill="y", padx=(12, 0))
        celda.pack_propagate(False)
        ctk.CTkLabel(
            celda, text=titulo.upper(), anchor="w",
            font=("Segoe UI", 10, "bold"),
            text_color=colores["subtext"]
        ).pack(anchor="w", expand=True)

    return fila
