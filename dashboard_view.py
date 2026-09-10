"""
views/dashboard_view.py
------------------------
Pantalla principal del sistema SIGITO después del login.
Muestra KPIs, gráficos de inventario y últimos movimientos.

INTEGRACIÓN CON EL BACKEND (Persona 1 y 4):
Los datos marcados con # TODO están hardcodeados por ahora.
Cuando los demás módulos estén listos, reemplazar con:
    - KPIs         → listar_articulos() agrupado por estado (Persona 1)
    - Movimientos  → listar_historial_por_articulo() de utils/auditoria.py (Persona 1)
    - Categorías   → listar_categorias() con conteo de artículos (Persona 1)
    - Asignaciones → listar_asignaciones_activas() agrupado por mes (Persona 3)

NOTA para main.py (Persona 1):
    El punto de entrada del sistema es main.py.
    El bloque if __name__ == '__main__' es solo para probar
    la vista de forma aislada mientras se desarrolla.
"""

import tkinter as tk
import customtkinter as ctk
from PIL import Image
from pathlib import Path
from datetime import date

from views.tema import COLORES, aplicar_tema, forzar_redibujo
from controllers import inventario_controller, asignacion_controller, reportes_controller
from controllers import auth_controller
from utils import auditoria


class Dashboard(ctk.CTkToplevel):

    def __init__(self, master, usuario=None, on_logout=None):
        super().__init__(master)

        self.usuario = usuario
        self.on_logout = on_logout
        self._vista_actual = "dashboard"
        self._after_paneles = None   # id del after() que arma el grid 2x2
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

        # --------------------------------------------------
        # Ajustar ventana al tamaño real de la pantalla
        # dejando espacio para la barra de tareas de Windows
        # --------------------------------------------------
        self.update_idletasks()
        ancho_pantalla  = self.winfo_screenwidth()
        alto_pantalla   = self.winfo_screenheight()
        alto_util       = alto_pantalla - 48   # resta barra de tareas (~48px)

        self.title("SIGITO")
        self.geometry(f"{ancho_pantalla}x{alto_util}+0+0")
        self.resizable(True, True)
        self.minsize(1100, 700)

        # --------------------------------------------------
        # Ruta Assets
        # --------------------------------------------------
        self.ASSETS = Path(__file__).parent.parent / "assets"

        # --------------------------------------------------
        # Colores desde views/tema.py
        # --------------------------------------------------
        self.COLOR_BACKGROUND = COLORES["dash_fondo"]
        self.COLOR_SIDEBAR    = COLORES["dash_sidebar"]
        self.COLOR_CONTENT    = COLORES["dash_content"]
        self.COLOR_CARD       = COLORES["dash_card"]
        self.COLOR_CARD_INNER = COLORES["dash_card_inner"]
        self.COLOR_BORDER     = COLORES["dash_borde"]
        self.COLOR_PRIMARY    = COLORES["azul_primario"]
        self.COLOR_TEXT       = COLORES["texto_oscuro"]
        self.COLOR_SUBTEXT    = COLORES["dash_subtext"]
        self.COLOR_FILA       = COLORES["dash_fila"]
        self.COLOR_LINK       = COLORES["dash_link"]

        self.configure(fg_color=self.COLOR_BACKGROUND)

        self.crear_fondo()
        self.crear_layout()
        forzar_redibujo(self)

        # Los gráficos se dibujan automáticamente cuando el canvas
        # recibe su tamaño real (bind Configure en crear_panel)

    def _bind_grafico(self, canvas, fn):
        """
        Vincula el dibujado del gráfico al evento Configure del canvas.
        Esto garantiza que el canvas ya tiene su tamaño real cuando se dibuja.
        Se redibuja también cuando el usuario cambia el tamaño de la ventana.

        Durante el armado del layout, <Configure> se dispara varias veces
        seguidas (el canvas va recibiendo tamaños intermedios). Antes eso
        redibujaba el gráfico completo 3-5 veces. Ahora se hace debounce:
        se agenda el dibujo con after() y cada nuevo Configure cancela el
        anterior, así solo se dibuja una vez con el tamaño ya estable. Se
        ignora además el Configure que no cambia el tamaño.
        """
        estado: dict = {"after": None, "size": None}

        def dibujar():
            estado["after"] = None
            if not canvas.winfo_exists():
                return
            canvas.configure(bg=self.COLOR_CARD_INNER)
            canvas.delete("all")
            fn(canvas)

        def al_redimensionar(event):
            size = (event.width, event.height)
            if size == estado["size"]:
                return
            estado["size"] = size
            if estado["after"] is not None:
                canvas.after_cancel(estado["after"])
            estado["after"] = canvas.after(60, dibujar)

        canvas.bind("<Configure>", al_redimensionar)

    # ==========================================================
    # FONDO
    # ==========================================================

    def crear_fondo(self):

        self.canvas_fondo = ctk.CTkCanvas(
            self,
            bg=self.COLOR_BACKGROUND,
            highlightthickness=0
        )
        self.canvas_fondo.place(relwidth=1, relheight=1)

        for x in range(0, 3000, 140):
            self.canvas_fondo.create_line(x, 0, x, 2000, fill=COLORES["dash_grid"])
        for y in range(0, 2000, 140):
            self.canvas_fondo.create_line(0, y, 3000, y, fill=COLORES["dash_grid"])

    # ==========================================================
    # LAYOUT
    # ==========================================================

    def crear_layout(self):

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=18, pady=18)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self.main,
            width=235,
            fg_color=self.COLOR_SIDEBAR,
            corner_radius=20,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.crear_sidebar()

        # Contenido
        self.content = ctk.CTkFrame(
            self.main,
            fg_color=self.COLOR_CONTENT,
            corner_radius=20,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        self.content.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self._mostrar_vista(self._vista_actual)

    # ==========================================================
    # SIDEBAR
    # ==========================================================

    def crear_sidebar(self):

        logo = self.cargar_imagen("logo.png", 80)
        ctk.CTkLabel(self.sidebar, image=logo, text="").pack(pady=(22, 10))

        ctk.CTkLabel(
            self.sidebar,
            text="SIGITO",
            font=("Segoe UI", 26, "bold"),
            text_color=self.COLOR_TEXT
        ).pack()

        ctk.CTkLabel(
            self.sidebar,
            text="Sistema de Gestión\nInventario Tecnológico",
            font=("Segoe UI", 12),
            text_color=self.COLOR_SUBTEXT,
            justify="center"
        ).pack(pady=(4, 16))

        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=self.COLOR_BORDER).pack(fill="x", padx=16, pady=(0, 16))

        # 6 botones de navegación acordados con el equipo
        self.boton_dashboard    = self.crear_boton_sidebar("dashboard.png",    "Dashboard")
        self.boton_inventario   = self.crear_boton_sidebar("inventario.png",   "Inventario")
        self.boton_asignaciones = self.crear_boton_sidebar("asignaciones.png", "Asignaciones")
        self.boton_reportes     = self.crear_boton_sidebar("reportes.png",     "Reportes")
        self.boton_usuarios     = self.crear_boton_sidebar("usuarios.png",     "Usuarios")
        self.boton_config       = self.crear_boton_sidebar("configuracion.png","Configuración")

        self._botones_nav = {
            "dashboard":    self.boton_dashboard,
            "inventario":   self.boton_inventario,
            "asignaciones": self.boton_asignaciones,
            "reportes":     self.boton_reportes,
            "usuarios":     self.boton_usuarios,
            "config":       self.boton_config,
        }

        self.boton_dashboard.configure(command=lambda: self._mostrar_vista("dashboard"))
        self.boton_inventario.configure(command=lambda: self._mostrar_vista("inventario"))
        self.boton_asignaciones.configure(command=lambda: self._mostrar_vista("asignaciones"))
        self.boton_reportes.configure(command=lambda: self._mostrar_vista("reportes"))
        self.boton_usuarios.configure(command=lambda: self._mostrar_vista("usuarios"))
        self.boton_config.configure(command=lambda: self._mostrar_vista("config"))
        self._resaltar_boton(self._vista_actual)

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True, fill="both")

        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=self.COLOR_BORDER).pack(fill="x", padx=16, pady=(8, 12))

        self.boton_toggle = ctk.CTkButton(
            self.sidebar,
            text="☀️  Modo Claro",
            width=200, height=36, corner_radius=10,
            fg_color="transparent",
            hover_color=COLORES["dash_hover"],
            text_color=self.COLOR_TEXT,
            font=("Segoe UI", 12),
            command=self._toggle_modo
        )
        self.boton_toggle.pack(padx=12, pady=(0, 6))

        ctk.CTkButton(
            self.sidebar,
            text="⬅  Cerrar sesión",
            width=200, height=36, corner_radius=10,
            fg_color="transparent",
            hover_color=COLORES["dash_hover"],
            text_color=self.COLOR_SUBTEXT,
            font=("Segoe UI", 12),
            command=self._cerrar_sesion
        ).pack(padx=12, pady=(0, 6))

        ctk.CTkLabel(
            self.sidebar,
            text="SIGITO v1.0",
            font=("Segoe UI", 11),
            text_color=self.COLOR_SUBTEXT
        ).pack(pady=(0, 20))

    def _toggle_modo(self):
        from views.tema import toggle_modo
        toggle_modo(self.boton_toggle)
        self._actualizar_colores()

    def _actualizar_colores(self):
        from views.tema import es_modo_oscuro
        oscuro = es_modo_oscuro()

        if oscuro:
            self.COLOR_BACKGROUND = COLORES["dash_fondo"]
            self.COLOR_SIDEBAR    = COLORES["dash_sidebar"]
            self.COLOR_CONTENT    = COLORES["dash_content"]
            self.COLOR_CARD       = COLORES["dash_card"]
            self.COLOR_CARD_INNER = COLORES["dash_card_inner"]
            self.COLOR_BORDER     = COLORES["dash_borde"]
            self.COLOR_TEXT       = COLORES["texto_oscuro"]
            self.COLOR_SUBTEXT    = COLORES["dash_subtext"]
            self.COLOR_FILA       = COLORES["dash_fila"]
            self.COLOR_LINK       = COLORES["dash_link"]
            grid_color            = COLORES["dash_grid"]
        else:
            self.COLOR_BACKGROUND = COLORES["dash_claro_fondo"]
            self.COLOR_SIDEBAR    = COLORES["dash_claro_sidebar"]
            self.COLOR_CONTENT    = COLORES["dash_claro_content"]
            self.COLOR_CARD       = COLORES["dash_claro_card"]
            self.COLOR_CARD_INNER = COLORES["dash_claro_card_inner"]
            self.COLOR_BORDER     = COLORES["dash_claro_borde"]
            self.COLOR_TEXT       = COLORES["texto_claro"]
            self.COLOR_SUBTEXT    = COLORES["dash_claro_subtext"]
            self.COLOR_FILA       = COLORES["dash_claro_fila"]
            self.COLOR_LINK       = COLORES["dash_claro_link"]
            grid_color            = "#D1D5DB"

        # Actualizar ventana principal
        self.configure(fg_color=self.COLOR_BACKGROUND)

        # Redibujar cuadrícula del fondo
        self.canvas_fondo.configure(bg=self.COLOR_BACKGROUND)
        self.canvas_fondo.delete("all")
        for x in range(0, 3000, 140):
            self.canvas_fondo.create_line(x, 0, x, 2000, fill=grid_color)
        for y in range(0, 2000, 140):
            self.canvas_fondo.create_line(0, y, 3000, y, fill=grid_color)

        # DESTRUIR y RECREAR todo el layout completo
        # (CustomTkinter no actualiza fg_color de frames existentes)
        self.main.destroy()
        self.crear_layout()

    def _resaltar_boton(self, nombre):
        for clave, boton in self._botones_nav.items():
            boton.configure(fg_color=self.COLOR_PRIMARY if clave == nombre else "transparent")

    def _mostrar_vista(self, nombre):
        self._vista_actual = nombre
        self._resaltar_boton(nombre)

        # Si había un armado de paneles del dashboard pendiente y se
        # cambia de vista antes de que corra, cancelarlo (dibujaría sobre
        # un contenedor ya destruido).
        if self._after_paneles is not None:
            self.after_cancel(self._after_paneles)
            self._after_paneles = None

        for hijo in self.content.winfo_children():
            hijo.destroy()

        if nombre == "dashboard":
            self.crear_header(self.content)
        elif nombre == "inventario":
            from views.inventario_view import InventarioView
            InventarioView(self.content).pack(fill="both", expand=True, padx=24, pady=20)
        elif nombre == "asignaciones":
            from views.asignacion_view import AsignacionView
            AsignacionView(self.content, usuario=self.usuario).pack(fill="both", expand=True, padx=24, pady=20)
        elif nombre == "reportes":
            from views.reportes_view import ReportesView
            ReportesView(self.content).pack(fill="both", expand=True, padx=24, pady=20)
        elif nombre == "usuarios":
            from views.usuarios_view import UsuariosView
            UsuariosView(self.content).pack(fill="both", expand=True, padx=24, pady=20)
        elif nombre == "config":
            from views.config_view import ConfigView
            ConfigView(self.content, usuario=self.usuario).pack(fill="both", expand=True, padx=24, pady=20)

    def _cerrar_sesion(self):
        auth_controller.cerrar_sesion()
        callback = self.on_logout
        self.destroy()
        if callback:
            callback()

    def _cerrar_aplicacion(self):
        self.master.destroy()

    # ==========================================================
    # BOTÓN SIDEBAR
    # ==========================================================

    def crear_boton_sidebar(self, icono, texto):

        imagen = self.cargar_imagen(icono, 20)

        boton = ctk.CTkButton(
            self.sidebar,
            width=200, height=44, corner_radius=10,
            image=imagen, text=texto,
            compound="left", anchor="w",
            fg_color="transparent",
            hover_color=COLORES["dash_hover"],
            text_color=self.COLOR_TEXT,
            font=("Segoe UI", 14, "bold"),
            border_width=0
        )
        boton.pack(padx=12, pady=3)
        return boton

    # ==========================================================
    # HEADER
    # ==========================================================

    def crear_header(self, padre):

        header = ctk.CTkFrame(padre, height=80, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 14))
        header.pack_propagate(False)

        izq = ctk.CTkFrame(header, fg_color="transparent")
        izq.pack(side="left", fill="y")

        nombre_usuario = self.usuario.nombre if self.usuario else "Administrador"

        ctk.CTkLabel(
            izq,
            text=f"Bienvenido, {nombre_usuario}",
            font=("Segoe UI", 24, "bold"),
            text_color=self.COLOR_TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            izq,
            text="Sistema de Gestión de Inventario Tecnológico",
            font=("Segoe UI", 13),
            text_color=self.COLOR_SUBTEXT
        ).pack(anchor="w", pady=(3, 0))

        der = ctk.CTkFrame(header, fg_color="transparent")
        der.pack(side="right", fill="y")

        ctk.CTkLabel(
            der,
            text=date.today().strftime("%d %B %Y"),
            font=("Segoe UI", 13),
            text_color=self.COLOR_SUBTEXT
        ).pack(anchor="e")

        ctk.CTkButton(
            der,
            text=nombre_usuario,
            width=140, height=36,
            fg_color=self.COLOR_PRIMARY,
            hover_color=COLORES["dash_hover_claro"],
            corner_radius=10,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(8, 0))

        self.crear_kpis(padre)

    # ==========================================================
    # KPIs
    # ==========================================================

    def crear_kpis(self, padre):

        contenedor = ctk.CTkFrame(padre, fg_color="transparent")
        contenedor.pack(fill="x", padx=24)

        # Se consulta una sola vez y se reutiliza en el donut (evita
        # repetir la misma consulta cuando <Configure> dispara el redibujo).
        self._resumen_estados = {
            fila["estado"]: fila["cantidad"] for fila in reportes_controller.resumen_articulos_por_estado()
        }
        resumen = self._resumen_estados
        disponibles = resumen.get("disponible", 0)
        prestados = resumen.get("prestado", 0)
        de_baja = resumen.get("de_baja", 0)
        total = disponibles + prestados + de_baja

        datos = [
            (str(total),        "Equipos"),
            (str(prestados),    "Prestados"),
            (str(de_baja),      "De baja"),
            (str(disponibles),  "Disponibles")
        ]

        for numero, texto in datos:
            card = ctk.CTkFrame(
                contenedor,
                fg_color=self.COLOR_CARD,
                corner_radius=16,
                border_width=1,
                border_color=self.COLOR_BORDER
            )
            card.pack(side="left", padx=(0, 14), expand=True, fill="both", ipady=10)

            ctk.CTkLabel(
                card, text=numero,
                font=("Segoe UI", 30, "bold"),
                text_color=self.COLOR_TEXT
            ).pack(pady=(16, 0))

            ctk.CTkLabel(
                card, text=texto,
                font=("Segoe UI", 13),
                text_color=self.COLOR_SUBTEXT
            ).pack(pady=(0, 16))

        # El grid 2x2 de paneles (gráficos + movimientos) es la parte más
        # cara del armado (~600 ms de widgets + 3 consultas). Se difiere un
        # tick para que la ventana ya aparezca con sidebar, header y KPIs;
        # los paneles se rellenan enseguida sin bloquear el primer pintado.
        self._after_paneles = self.after(10, self._armar_paneles, padre)

    def _armar_paneles(self, padre):
        self._after_paneles = None
        if self._vista_actual != "dashboard" or not padre.winfo_exists():
            return
        self.crear_dashboard(padre)

    # ==========================================================
    # DASHBOARD (grid 2x2)
    # ==========================================================

    def crear_dashboard(self, padre):

        # Se consultan una sola vez y se reutilizan en cada redibujo del
        # canvas (evita repetir la consulta cada vez que <Configure> dispara).
        self._datos_categoria    = reportes_controller.articulos_por_categoria()
        self._datos_asignaciones = reportes_controller.asignaciones_por_mes(meses=6)

        dashboard = ctk.CTkFrame(padre, fg_color="transparent")
        dashboard.pack(fill="both", expand=True, padx=24, pady=(14, 20))

        dashboard.grid_rowconfigure(0, weight=1, uniform="fila")
        dashboard.grid_rowconfigure(1, weight=1, uniform="fila")
        dashboard.grid_columnconfigure(0, weight=1, uniform="col")
        dashboard.grid_columnconfigure(1, weight=1, uniform="col")

        self.crear_panel(dashboard, "Estado del inventario", "Equipos disponibles",        "panel_estado",       0, 0)
        self.crear_panel(dashboard, "Últimos movimientos",   "Actividad reciente",          "panel_movimientos",  0, 1)
        self.crear_panel(dashboard, "Equipos por categoría", "Cantidad por tipo de equipo", "panel_categoria",    1, 0)
        self.crear_panel(dashboard, "Asignaciones por mes",  "Últimos seis meses",          "panel_asignaciones", 1, 1)

    # ==========================================================
    # PANEL
    # ==========================================================

    def crear_panel(self, padre, titulo, subtitulo, tipo, fila, col):

        panel = ctk.CTkFrame(
            padre,
            fg_color=self.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        panel.grid(row=fila, column=col, sticky="nsew", padx=8, pady=8)
        panel.grid_propagate(False)

        ctk.CTkLabel(
            panel, text=titulo,
            font=("Segoe UI", 14, "bold"),
            text_color=self.COLOR_TEXT
        ).pack(anchor="w", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            panel, text=subtitulo,
            font=("Segoe UI", 10),
            text_color=self.COLOR_SUBTEXT
        ).pack(anchor="w", padx=16, pady=(2, 6))

        contenido = ctk.CTkFrame(panel, fg_color=self.COLOR_CARD_INNER, corner_radius=10, border_width=0)
        contenido.pack(fill="both", expand=True, padx=12, pady=(2, 12))

        # Crear canvas placeholder y registrar el gráfico para dibujarlo después
        if tipo == "panel_movimientos":
            self.crear_panel_movimientos(contenido)
        else:
            canvas = ctk.CTkCanvas(contenido, bg=self.COLOR_CARD_INNER,
                                   highlightthickness=0)
            canvas.pack(fill="both", expand=True, padx=6, pady=6)

            if   tipo == "panel_categoria":    self._bind_grafico(canvas, self._dibujar_barras)
            elif tipo == "panel_asignaciones": self._bind_grafico(canvas, self._dibujar_linea)
            elif tipo == "panel_estado":       self._bind_grafico(canvas, self._dibujar_donut)

    # ==========================================================
    # GRÁFICO BARRAS — Equipos por categoría
    # ==========================================================

    def _dibujar_barras(self, canvas):

        filas = self._datos_categoria
        categorias = [fila["categoria"] for fila in filas]
        cantidades  = [fila["cantidad"] for fila in filas]

        if not cantidades or max(cantidades) == 0:
            return

        w       = canvas.winfo_width()
        h       = canvas.winfo_height()
        max_val = max(cantidades)
        n       = len(categorias)
        mg_x    = 28
        mg_y    = 18
        espacio = (w - mg_x * 2) / n
        ancho_b = espacio * 0.52

        for i, (cat, val) in enumerate(zip(categorias, cantidades)):
            x0     = mg_x + i * espacio + (espacio - ancho_b) / 2
            x1     = x0 + ancho_b
            alto_b = (val / max_val) * (h - mg_y * 2 - 22)
            y0     = h - mg_y - alto_b
            y1     = h - mg_y

            # Barra con esquinas superiores redondeadas simuladas
            radio = 4
            canvas.create_rectangle(x0, y0 + radio, x1, y1,
                                    fill=self.COLOR_PRIMARY, outline="")
            canvas.create_rectangle(x0, y0, x1 - radio, y0 + radio,
                                    fill=self.COLOR_PRIMARY, outline="")
            canvas.create_oval(x0, y0, x0 + radio * 2, y0 + radio * 2,
                               fill=self.COLOR_PRIMARY, outline="")
            canvas.create_oval(x1 - radio * 2, y0, x1, y0 + radio * 2,
                               fill=self.COLOR_PRIMARY, outline="")

            canvas.create_text((x0 + x1) / 2, y0 - 9,
                               text=str(val), fill=self.COLOR_TEXT,
                               font=("Segoe UI", 9, "bold"))
            canvas.create_text((x0 + x1) / 2, h - 7,
                               text=cat, fill=self.COLOR_SUBTEXT,
                               font=("Segoe UI", 8))

    # ==========================================================
    # GRÁFICO LÍNEA — Asignaciones por mes
    # ==========================================================

    def _dibujar_linea(self, canvas):

        _MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        filas = self._datos_asignaciones
        meses     = [_MESES_ES[int(fila["mes"].split("-")[1]) - 1] for fila in filas]
        prestamos = [fila["cantidad"] for fila in filas]

        if len(prestamos) < 2 or max(prestamos) == 0:
            return

        w       = canvas.winfo_width()
        h       = canvas.winfo_height()
        max_val = max(prestamos)
        n       = len(meses)
        mg_x    = 28
        mg_y    = 18

        espacio = (w - mg_x * 2) / (n - 1)

        def px(i): return mg_x + i * espacio
        def py(v): return h - mg_y - (v / max_val) * (h - mg_y * 2 - 16)

        puntos = [(px(i), py(v)) for i, v in enumerate(prestamos)]

        # Área rellena
        poligono = [mg_x, h - mg_y]
        for x, y in puntos:
            poligono += [x, y]
        poligono += [px(n - 1), h - mg_y]
        # Color del area: azul oscuro en modo oscuro, azul claro en modo claro
        from views.tema import es_modo_oscuro
        area_color = "#1A3A6B" if es_modo_oscuro() else "#C7D8F0"
        canvas.create_polygon(poligono, fill=area_color, outline="")

        # Línea
        for i in range(len(puntos) - 1):
            canvas.create_line(puntos[i], puntos[i + 1],
                               fill=self.COLOR_PRIMARY, width=2, smooth=True)

        # Puntos y etiquetas
        for i, (x, y) in enumerate(puntos):
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4,
                               fill=self.COLOR_PRIMARY, outline=self.COLOR_CARD_INNER, width=2)
            canvas.create_text(x, h - 7, text=meses[i],
                               fill=self.COLOR_SUBTEXT, font=("Segoe UI", 8))

        # Valores sobre los puntos
        for x, y, v in [(px(i), py(v), v) for i, v in enumerate(prestamos)]:
            canvas.create_text(x, y - 12, text=str(v),
                               fill="white", font=("Segoe UI", 8, "bold"))

    # ==========================================================
    # GRÁFICO DONUT — Estado del inventario
    # ==========================================================

    def _dibujar_donut(self, canvas):

        resumen = self._resumen_estados
        _ETIQUETAS = {"disponible": "Disponibles", "prestado": "Prestados", "de_baja": "De baja"}
        _COLORES_ESTADO = {
            "disponible": COLORES["disponible_texto"],
            "prestado":   COLORES["danado_texto"],
            "de_baja":    COLORES["de_baja_texto"],
        }

        etiquetas, valores, colores_d = [], [], []
        for estado in ("disponible", "prestado", "de_baja"):
            if resumen.get(estado, 0) > 0:
                etiquetas.append(_ETIQUETAS[estado])
                valores.append(resumen[estado])
                colores_d.append(_COLORES_ESTADO[estado])

        if not valores:
            return

        w     = canvas.winfo_width()
        h     = canvas.winfo_height()

        # Zona del donut: mitad izquierda del canvas
        zona_d = w * 0.52
        cx     = zona_d / 2
        cy     = h / 2
        r_ext  = min(zona_d, h) / 2 - 14
        r_int  = r_ext * 0.60
        total  = sum(valores)
        angulo = -90.0

        for val, color in zip(valores, colores_d):
            grados = (val / total) * 360
            canvas.create_arc(
                cx - r_ext, cy - r_ext, cx + r_ext, cy + r_ext,
                start=angulo, extent=grados,
                fill=color, outline=self.COLOR_CARD_INNER, width=3
            )
            angulo += grados

        # Hueco interior
        canvas.create_oval(cx - r_int, cy - r_int, cx + r_int, cy + r_int,
                           fill=self.COLOR_CARD_INNER,
                           outline=self.COLOR_CARD_INNER)

        # Texto central dentro del hueco — % de disponibles si hay dato,
        # si no, % de la primera etiqueta presente
        indice_disp = etiquetas.index("Disponibles") if "Disponibles" in etiquetas else 0
        porcentaje = int((valores[indice_disp] / total) * 100)
        canvas.create_text(cx, cy - 8, text=f"{porcentaje}%",
                           fill=self.COLOR_TEXT, font=("Segoe UI", 13, "bold"))
        canvas.create_text(cx, cy + 10, text=etiquetas[indice_disp].upper(),
                           fill=self.COLOR_SUBTEXT, font=("Segoe UI", 7))

        # Leyenda — zona derecha del canvas
        x_ley  = zona_d + 10
        y_ley  = cy - (len(etiquetas) * 18) / 2

        for etiqueta, color, valor in zip(etiquetas, colores_d, valores):
            canvas.create_rectangle(x_ley, y_ley, x_ley + 10, y_ley + 10,
                                    fill=color, outline="")
            canvas.create_text(x_ley + 16, y_ley + 5,
                               text=f"{etiqueta} ({valor})",
                               fill=self.COLOR_TEXT,
                               font=("Segoe UI", 9), anchor="w")
            y_ley += 22

    # ==========================================================
    # PANEL ÚLTIMOS MOVIMIENTOS
    # ==========================================================

    def _color_avatar(self, nombre):
        """
        Genera un color de avatar consistente basado en el nombre.
        El mismo nombre siempre produce el mismo color.
        """
        colores_avatar = [
            "#3B82F6",  # azul
            "#8B5CF6",  # morado
            "#10B981",  # verde
            "#F59E0B",  # amarillo
            "#EF4444",  # rojo
            "#06B6D4",  # cyan
            "#EC4899",  # rosa
            "#6366F1",  # indigo
        ]
        indice = sum(ord(c) for c in nombre) % len(colores_avatar)
        return colores_avatar[indice]

    def _iniciales(self, nombre):
        """Extrae las iniciales del nombre (ej. 'Juan Pérez' -> 'JP')."""
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return partes[0][:2].upper()

    def crear_panel_movimientos(self, frame):

        movimientos = [
            (
                fila["usuario_nombre"] or "Sistema",
                fila["detalle"] or fila["tipo_movimiento"],
                fila["fecha"].strftime("%H:%M")
            )
            for fila in auditoria.listar_historial_reciente(limite=10)
        ]

        contenedor = ctk.CTkScrollableFrame(
            frame,
            fg_color="transparent",
            scrollbar_button_color=self.COLOR_BORDER,
            scrollbar_button_hover_color=COLORES["dash_hover_claro"]
        )
        contenedor.pack(fill="both", expand=True, padx=6, pady=6)

        for nombre, accion, hora in movimientos:

            fila = ctk.CTkFrame(contenedor, fg_color=self.COLOR_FILA,
                                corner_radius=12, height=58)
            fila.pack(fill="x", pady=4, padx=2)
            fila.pack_propagate(False)

            # --- Avatar circular con iniciales ---
            color_av = self._color_avatar(nombre)
            iniciales = self._iniciales(nombre)

            avatar_frame = ctk.CTkFrame(
                fila,
                width=36, height=36,
                fg_color=color_av,
                corner_radius=18   # círculo perfecto
            )
            avatar_frame.pack(side="left", padx=(12, 10), pady=11)
            avatar_frame.pack_propagate(False)

            ctk.CTkLabel(
                avatar_frame,
                text=iniciales,
                font=("Segoe UI", 12, "bold"),
                text_color="#FFFFFF"
            ).place(relx=0.5, rely=0.5, anchor="center")

            # --- Texto: nombre + acción en dos líneas ---
            texto_frame = ctk.CTkFrame(fila, fg_color="transparent")
            texto_frame.pack(side="left", fill="both", expand=True, pady=8)

            ctk.CTkLabel(
                texto_frame,
                text=nombre,
                anchor="w",
                font=("Segoe UI", 12, "bold"),
                text_color=self.COLOR_TEXT
            ).pack(anchor="w")

            ctk.CTkLabel(
                texto_frame,
                text=accion,
                anchor="w",
                font=("Segoe UI", 10),
                text_color=self.COLOR_SUBTEXT
            ).pack(anchor="w")

            # --- Hora ---
            ctk.CTkLabel(
                fila,
                text=hora,
                width=42,
                font=("Segoe UI", 11, "bold"),
                text_color=self.COLOR_LINK
            ).pack(side="right", padx=12)

    # ==========================================================
    # CARGAR IMAGEN
    # ==========================================================

    _CACHE_IMAGENES = {}

    def cargar_imagen(self, nombre, tamaño):

        clave = (nombre, tamaño)
        if clave in Dashboard._CACHE_IMAGENES:
            return Dashboard._CACHE_IMAGENES[clave]

        ruta = self.ASSETS / nombre

        if not ruta.exists():
            return None

        imagen = Image.open(ruta)
        imagen.thumbnail((tamaño, tamaño), Image.LANCZOS)

        ctk_imagen = ctk.CTkImage(
            light_image=imagen,
            dark_image=imagen,
            size=imagen.size
        )
        Dashboard._CACHE_IMAGENES[clave] = ctk_imagen
        return ctk_imagen


# ==========================================================
# SOLO PARA PRUEBAS AISLADAS — en producción usar main.py
# ==========================================================

if __name__ == "__main__":
    aplicar_tema()
    _root = ctk.CTk()
    _root.withdraw()
    app = Dashboard(_root)
    app.protocol("WM_DELETE_WINDOW", _root.destroy)
    _root.mainloop()