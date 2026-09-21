"""
views/historial_view.py — Pantalla de historial de auditoría.

Frame embebido dentro del área de contenido del Dashboard (mismo patrón
que inventario/reportes). Muestra utils/auditoria.listar_historial():
todos los movimientos registrados (alta, préstamo, devolución, baja,
mantenimiento) con filtro por tipo y texto libre, paginado de a 10.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from utils.auditoria import listar_historial
from utils.exportador import exportar_csv, exportar_excel
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO, color_badge
from views.componentes import crear_card, crear_encabezado, crear_encabezado_tabla, crear_fila_tabla, crear_badge

_TIPOS = {
    "Todos los movimientos": None,
    "Alta": "alta",
    "Préstamo": "prestamo",
    "Devolución": "devolucion",
    "Baja": "baja",
    "Mantenimiento": "mantenimiento",
}

_COLOR_POR_TIPO = {
    "alta": "disponible",
    "prestamo": "en_uso",
    "devolucion": "devuelto",
    "baja": "de_baja",
    "mantenimiento": "regular",
}


class HistorialView(ctk.CTkFrame):

    ANCHOS = (140, 110, 170, 140, 300)
    TAMANO_PAGINA = 10

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.c = colores_dashboard()
        self._historial_filtrado = []
        self._pagina_actual = 0

        self._construir_layout()
        self._cargar_historial()

    # ------------------------------------------------------------
    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        encabezado = ctk.CTkFrame(contenedor, fg_color="transparent")
        encabezado.pack(fill="x")

        crear_encabezado(
            encabezado, self.c,
            "Historial de auditoría",
            "Registro de todos los movimientos: altas, préstamos, devoluciones, bajas y mantenimientos."
        ).pack(side="left")

        botones = ctk.CTkFrame(encabezado, fg_color="transparent")
        botones.pack(side="right", anchor="e")

        ctk.CTkButton(botones, text="Exportar CSV", width=120,
                      command=lambda: self._exportar(exportar_csv, ".csv"),
                      **ESTILO_BOTON_SECUNDARIO).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botones, text="Exportar Excel", width=130,
                      command=lambda: self._exportar(exportar_excel, ".xlsx"),
                      **ESTILO_BOTON_PRIMARIO).pack(side="left")

        fila_filtros = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_filtros.pack(fill="x", pady=(16, 12))

        self.entrada_busqueda = ctk.CTkEntry(
            fila_filtros, placeholder_text="Buscar por artículo, código, usuario o detalle...",
        )
        self.entrada_busqueda.pack(side="left", fill="x", expand=True)
        self.entrada_busqueda.bind("<KeyRelease>", lambda _e: self._cargar_historial())

        self.combo_tipo = ctk.CTkComboBox(
            fila_filtros, width=190, state="readonly",
            values=list(_TIPOS.keys()), command=lambda _v: self._cargar_historial(),
        )
        self.combo_tipo.set("Todos los movimientos")
        self.combo_tipo.pack(side="left", padx=(10, 0))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior, self.c,
            ["Fecha", "Tipo", "Artículo", "Usuario", "Detalle"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

        fila_paginacion = ctk.CTkFrame(interior, fg_color="transparent")
        fila_paginacion.pack(fill="x", pady=(10, 0))

        self.boton_pagina_anterior = ctk.CTkButton(
            fila_paginacion, text="< Anterior", width=110,
            command=self._pagina_anterior, **ESTILO_BOTON_SECUNDARIO
        )
        self.boton_pagina_anterior.pack(side="left")

        self.etiqueta_paginacion = ctk.CTkLabel(
            fila_paginacion, text="", text_color=self.c["subtext"], font=("Segoe UI", 12)
        )
        self.etiqueta_paginacion.pack(side="left", expand=True)

        self.boton_pagina_siguiente = ctk.CTkButton(
            fila_paginacion, text="Siguiente >", width=110,
            command=self._pagina_siguiente, **ESTILO_BOTON_SECUNDARIO
        )
        self.boton_pagina_siguiente.pack(side="right")

    # ------------------------------------------------------------
    def _cargar_historial(self):
        tipo = _TIPOS.get(self.combo_tipo.get())
        texto = self.entrada_busqueda.get().strip() or None

        self._historial_filtrado = listar_historial(tipo_movimiento=tipo, filtro_texto=texto)
        self._pagina_actual = 0
        self._renderizar_pagina()

    def _total_paginas(self):
        total = len(self._historial_filtrado)
        if total == 0:
            return 1
        return (total - 1) // self.TAMANO_PAGINA + 1

    def _pagina_anterior(self):
        if self._pagina_actual > 0:
            self._pagina_actual -= 1
            self._renderizar_pagina()

    def _pagina_siguiente(self):
        if self._pagina_actual < self._total_paginas() - 1:
            self._pagina_actual += 1
            self._renderizar_pagina()

    def _renderizar_pagina(self):
        inicio = self._pagina_actual * self.TAMANO_PAGINA
        fin = inicio + self.TAMANO_PAGINA
        filas_pagina = self._historial_filtrado[inicio:fin]

        for hijo in self.lista.winfo_children():
            hijo.destroy()

        total = len(self._historial_filtrado)
        total_paginas = self._total_paginas()
        if total == 0:
            self.etiqueta_paginacion.configure(text="Sin movimientos")
        else:
            self.etiqueta_paginacion.configure(
                text=f"Mostrando {inicio + 1}–{min(fin, total)} de {total} "
                     f"(página {self._pagina_actual + 1} de {total_paginas})"
            )
        self.boton_pagina_anterior.configure(state="normal" if self._pagina_actual > 0 else "disabled")
        self.boton_pagina_siguiente.configure(
            state="normal" if self._pagina_actual < total_paginas - 1 else "disabled"
        )

        for fila in filas_pagina:
            estado_color = _COLOR_POR_TIPO.get(fila["tipo_movimiento"], "de_baja")
            fondo, texto_color = color_badge(estado_color)

            def _celda_tipo(celda, tipo=fila["tipo_movimiento"], fondo=fondo, texto_color=texto_color):
                crear_badge(celda, tipo.replace("_", " ").title(), fondo, texto_color).place(
                    relx=0, rely=0.5, anchor="w"
                )

            articulo_texto = fila["codigo_inventario"] or "—"
            if fila["articulo_nombre"]:
                articulo_texto = f"{fila['articulo_nombre']} ({articulo_texto})"

            crear_fila_tabla(
                self.lista, self.c,
                [
                    fila["fecha"].strftime("%Y-%m-%d %H:%M") if fila["fecha"] else "—",
                    _celda_tipo,
                    articulo_texto,
                    fila["usuario_nombre"] or "Sistema",
                    fila["detalle"] or "—",
                ],
                self.ANCHOS,
            )

    def _exportar(self, funcion_exportar, extension):
        if not self._historial_filtrado:
            messagebox.showwarning("Aviso", "No hay movimientos para exportar.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=extension, initialfile=f"historial{extension}")
        if not ruta:
            return
        datos = [
            {
                "fecha": fila["fecha"].strftime("%Y-%m-%d %H:%M") if fila["fecha"] else "",
                "tipo_movimiento": fila["tipo_movimiento"],
                "codigo_inventario": fila["codigo_inventario"] or "",
                "articulo": fila["articulo_nombre"] or "",
                "usuario": fila["usuario_nombre"] or "Sistema",
                "detalle": fila["detalle"] or "",
            }
            for fila in self._historial_filtrado
        ]
        try:
            funcion_exportar(datos, ruta)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo exportar:\n{error}")
            return
        messagebox.showinfo("Éxito", f"Historial exportado a:\n{ruta}")
