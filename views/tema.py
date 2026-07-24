"""
views/tema.py
--------------
Paleta de colores, tipografía y configuración visual de SIGITO.
Define el estilo base del sistema incluyendo el toggle entre
modo oscuro y claro.

INSTRUCCIONES (Persona 5 - Diseño):

1. TODOS los views deben importar de aquí — nadie define colores
   propios en sus archivos de vista. Si necesitas un color nuevo,
   agrégalo aquí y úsalo desde todos lados.
2. Llamar a `aplicar_tema()` una sola vez al inicio de `main.py`,
   antes de crear cualquier ventana.
3. Para el toggle de modo oscuro/claro, usar `toggle_modo()` —
   ya está conectado a CustomTkinter internamente.
4. Para los badges de estado de artículos y asignaciones, usar
   `color_badge(estado)` en vez de definir colores inline en cada vista.

Dependencia:
    pip install customtkinter
"""

import customtkinter as ctk


# ---------------------------------------------------------
# Paleta de colores (extraída de los diseños del equipo)
# Colores base: #1D4ED8, #06B6D4, #1F2937, #E5E7EB, #FFFFFF
# ---------------------------------------------------------
COLORES = {
    # Primarios (iguales en ambos modos)
    "azul_primario":        "#1D4ED8",
    "azul_hover":           "#1E40AF",
    "cyan_acento":          "#06B6D4",
    "cyan_hover":           "#0891B2",

    # Sidebar (siempre oscuro en ambos modos — decisión de diseño)
    "sidebar_fondo":        "#1F2937",
    "sidebar_item_activo":  "#1D4ED8",
    "sidebar_item_hover":   "#374151",
    "sidebar_texto":        "#F9FAFB",
    "sidebar_texto_sub":    "#9CA3AF",

    # Fondos modo oscuro
    "fondo_oscuro":         "#111827",
    "card_oscuro":          "#1F2937",
    "card_borde_oscuro":    "#374151",
    "input_oscuro":         "#374151",
    "texto_oscuro":         "#F9FAFB",
    "texto_sec_oscuro":     "#9CA3AF",

    # Fondos modo claro
    "fondo_claro":          "#F3F4F6",
    "card_claro":           "#FFFFFF",
    "card_borde_claro":     "#E5E7EB",
    "input_claro":          "#F9FAFB",
    "texto_claro":          "#111827",
    "texto_sec_claro":      "#6B7280",

    # Dashboard modo claro — equivalentes claros de la paleta oscura
    "dash_claro_fondo":     "#F0F4F8",   # fondo general ventana
    "dash_claro_content":   "#FFFFFF",   # área de contenido
    "dash_claro_card":      "#FFFFFF",   # tarjetas KPI y paneles
    "dash_claro_card_inner":"#F1F5F9",   # interior de paneles (gráficos)
    "dash_claro_fila":      "#E8EFF6",   # filas de movimientos
    "dash_claro_borde":     "#CBD5E1",   # bordes
    "dash_claro_subtext":   "#64748B",   # texto secundario
    "dash_claro_link":      "#2563EB",   # color de hora en movimientos
    "dash_claro_sidebar":   "#FFFFFF",   # fondo del sidebar en modo claro

    # Estados de artículos (iguales en ambos modos)
    "disponible_fondo":     "#DCFCE7",
    "disponible_texto":     "#16A34A",
    "en_uso_fondo":         "#DBEAFE",
    "en_uso_texto":         "#2563EB",
    "atrasado_fondo":       "#FEE2E2",
    "atrasado_texto":       "#DC2626",
    "danado_fondo":         "#FEF9C3",
    "danado_texto":         "#CA8A04",
    "de_baja_fondo":        "#F3F4F6",
    "de_baja_texto":        "#6B7280",

    # Alertas y notificaciones
    "error":                "#DC2626",
    "exito":                "#16A34A",
    "advertencia":          "#D97706",
    "info":                 "#2563EB",

    # Dashboard — fondos profundos (modo oscuro)
    # Paleta azul marino oscura usada en dashboard_view.py
    "dash_fondo":           "#08111F",   # fondo general de la ventana
    "dash_sidebar":         "#101B2D",   # fondo del sidebar
    "dash_content":         "#0D1626",   # fondo del área de contenido
    "dash_card":            "#162338",   # fondo de tarjetas/paneles
    "dash_card_inner":      "#111D30",   # fondo interior de paneles (gráficos)
    "dash_fila":            "#1A263A",   # fondo de filas en panel de movimientos
    "dash_borde":           "#314863",   # color de bordes y líneas divisoras
    "dash_subtext":         "#9FB0C5",   # texto secundario del dashboard
    "dash_link":            "#6FA8FF",   # texto de hora en movimientos
    "dash_hover":           "#1B2D47",   # hover de botones del sidebar
    "dash_grid":            "#13263E",   # líneas de la cuadrícula del fondo
    "dash_hover_claro":     "#3D98FF",   # hover de botones azules y scrollbar
    "dash_eje":             "#5C6B80",   # color de ejes en gráficas matplotlib
    "dash_texto_donut":     "#AAB7C4",   # texto secundario dentro del donut
}

# ---------------------------------------------------------
# Modo actual (para consultar desde cualquier view)
# ---------------------------------------------------------
_modo_actual = ["dark"]   # lista para poder mutar desde funciones internas


def get_modo():
    """Devuelve el modo actual: 'dark' o 'light'."""
    return _modo_actual[0]


def es_modo_oscuro():
    """Devuelve True si el modo actual es oscuro."""
    return _modo_actual[0] == "dark"


# ---------------------------------------------------------
# Colores dinámicos según el modo actual
# Usar estas funciones en los views en vez de COLORES directo
# cuando el color cambia entre modos.
# ---------------------------------------------------------
def color_fondo():
    return COLORES["fondo_oscuro"] if es_modo_oscuro() else COLORES["fondo_claro"]

def color_card():
    return COLORES["card_oscuro"] if es_modo_oscuro() else COLORES["card_claro"]

def color_borde():
    return COLORES["card_borde_oscuro"] if es_modo_oscuro() else COLORES["card_borde_claro"]

def color_input():
    return COLORES["input_oscuro"] if es_modo_oscuro() else COLORES["input_claro"]

def color_texto():
    return COLORES["texto_oscuro"] if es_modo_oscuro() else COLORES["texto_claro"]

def color_texto_secundario():
    return COLORES["texto_sec_oscuro"] if es_modo_oscuro() else COLORES["texto_sec_claro"]


# ---------------------------------------------------------
# Paleta del Dashboard (y demás ventanas internas: inventario,
# asignaciones, reportes, usuarios) según el modo actual.
# Centraliza lo que dashboard_view.py resuelve en _actualizar_colores,
# para que las demás vistas usen exactamente los mismos tonos.
# ---------------------------------------------------------
def colores_dashboard():
    if es_modo_oscuro():
        return {
            "fondo":       COLORES["dash_fondo"],
            "sidebar":     COLORES["dash_sidebar"],
            "content":     COLORES["dash_content"],
            "card":        COLORES["dash_card"],
            "card_inner":  COLORES["dash_card_inner"],
            "borde":       COLORES["dash_borde"],
            "texto":       COLORES["texto_oscuro"],
            "subtext":     COLORES["dash_subtext"],
            "fila":        COLORES["dash_fila"],
            "link":        COLORES["dash_link"],
            "grid":        COLORES["dash_grid"],
        }
    return {
        "fondo":       COLORES["dash_claro_fondo"],
        "sidebar":     COLORES["dash_claro_sidebar"],
        "content":     COLORES["dash_claro_content"],
        "card":        COLORES["dash_claro_card"],
        "card_inner":  COLORES["dash_claro_card_inner"],
        "borde":       COLORES["dash_claro_borde"],
        "texto":       COLORES["texto_claro"],
        "subtext":     COLORES["dash_claro_subtext"],
        "fila":        COLORES["dash_claro_fila"],
        "link":        COLORES["dash_claro_link"],
        "grid":        "#D1D5DB",
    }


# ---------------------------------------------------------
# Badges de estado (artículos y asignaciones)
# Devuelve (color_fondo, color_texto) según el estado
# ---------------------------------------------------------
def color_badge(estado):
    """
    Devuelve (fondo, texto) del badge según el estado.

    Uso en inventario_view.py o asignacion_view.py:
        fondo, texto = color_badge(articulo.estado_disponibilidad)
        badge = ctk.CTkLabel(frame, text=estado, fg_color=fondo, text_color=texto)
    """
    mapa = {
        "disponible":   (COLORES["disponible_fondo"],   COLORES["disponible_texto"]),
        "prestado":     (COLORES["en_uso_fondo"],        COLORES["en_uso_texto"]),
        "en_uso":       (COLORES["en_uso_fondo"],        COLORES["en_uso_texto"]),
        "atrasado":     (COLORES["atrasado_fondo"],      COLORES["atrasado_texto"]),
        "devuelto":     (COLORES["disponible_fondo"],    COLORES["disponible_texto"]),
        "dañado":       (COLORES["danado_fondo"],        COLORES["danado_texto"]),
        "danado":       (COLORES["danado_fondo"],        COLORES["danado_texto"]),
        "de_baja":      (COLORES["de_baja_fondo"],       COLORES["de_baja_texto"]),
        "bueno":        (COLORES["disponible_fondo"],    COLORES["disponible_texto"]),
        "regular":      (COLORES["danado_fondo"],        COLORES["danado_texto"]),
    }
    return mapa.get(estado, (COLORES["de_baja_fondo"], COLORES["de_baja_texto"]))


# ---------------------------------------------------------
# Toggle de modo oscuro/claro
# Llamar desde el botón en main_menu_view.py
# ---------------------------------------------------------
def toggle_modo(btn_toggle=None):
    """
    Alterna entre modo oscuro y claro.
    Si se pasa el botón del toggle, actualiza su texto automáticamente.

    Uso en main_menu_view.py:
        btn = ctk.CTkButton(sidebar, text="☀️ Modo Claro",
                            command=lambda: toggle_modo(btn))
    """
    if es_modo_oscuro():
        ctk.set_appearance_mode("light")
        _modo_actual[0] = "light"
        if btn_toggle:
            btn_toggle.configure(text="🌙 Modo Oscuro")
    else:
        ctk.set_appearance_mode("dark")
        _modo_actual[0] = "dark"
        if btn_toggle:
            btn_toggle.configure(text="☀️ Modo Claro")


# ---------------------------------------------------------
# Aplicar tema global (llamar UNA SOLA VEZ en main.py)
# ---------------------------------------------------------
def aplicar_tema():
    """
    Configura CustomTkinter con el tema base de SIGITO.
    Llamar antes de crear cualquier ventana, en main.py:

        from views.tema import aplicar_tema
        aplicar_tema()
        root = ctk.CTk()
    """
    ctk.set_default_color_theme("blue")
    ctk.set_appearance_mode("dark")   # modo oscuro por defecto
    _modo_actual[0] = "dark"


# ---------------------------------------------------------
# Estilos reutilizables para widgets comunes
# Usar como **kwargs al crear el widget
# ---------------------------------------------------------
ESTILO_BOTON_PRIMARIO = {
    "fg_color":         COLORES["azul_primario"],
    "hover_color":      COLORES["azul_hover"],
    "text_color":       "#FFFFFF",
    "corner_radius":    6,
    "font":             ("Inter", 13, "bold"),
}

ESTILO_BOTON_SECUNDARIO = {
    "fg_color":         "transparent",
    "hover_color":      COLORES["sidebar_item_hover"],
    "text_color":       COLORES["azul_primario"],
    "border_color":     COLORES["azul_primario"],
    "border_width":     1,
    "corner_radius":    6,
    "font":             ("Inter", 13),
}

ESTILO_INPUT = {
    "corner_radius":    6,
    "border_color":     COLORES["card_borde_oscuro"],
    "font":             ("Inter", 13),
}

ESTILO_TITULO = {
    "font":             ("Inter", 22, "bold"),
}

ESTILO_SUBTITULO = {
    "font":             ("Inter", 13),
    "text_color":       COLORES["texto_sec_oscuro"],
}

ESTILO_LABEL = {
    "font":             ("Inter", 13),
}