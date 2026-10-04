"""
views/reportes_view.py — Pantalla de reportes.

Frame embebido dentro del área de contenido del Dashboard (se muestra
al navegar desde el sidebar, reemplazando la vista anterior): arma su
layout con los colores de views/tema.py y los componentes compartidos
de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import os
import tempfile

import customtkinter as ctk
from tkinter import filedialog, messagebox

from controllers.reportes_controller import (
    resumen_articulos_por_estado, prestamos_vencidos, articulos_mas_prestados
)
from controllers.asignacion_controller import (
    alumnos_marcados, MARCA_NO_CUIDA, MARCA_TARDISTA, MARCA_AMBAS,
    DANOS_PARA_NO_CUIDA, TARDANZAS_PARA_TARDISTA,
)
from utils.exportador import (
    exportar_csv_secciones, exportar_excel_secciones, exportar_pdf_secciones
)
from utils.sistema import abrir_archivo
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card, crear_encabezado_tabla, crear_fila_tabla, crear_badge
)


class ReportesView(ctk.CTkFrame):

    ANCHOS = (110, 220, 200, 170)
    ANCHOS_RANKING = (40, 110, 240, 160, 120, 100)
    ANCHOS_MARCADOS = (220, 110, 220, 110, 110, 170)
    COLORES_MARCA = {
        MARCA_NO_CUIDA: ("danado_fondo", "danado_texto"),
        MARCA_TARDISTA: ("tardista_fondo", "tardista_texto"),
        MARCA_AMBAS:    ("atrasado_fondo", "atrasado_texto"),
    }
    # Texto del selector -> periodo de articulos_mas_prestados().
    PERIODOS = {"Hoy": "dia", "Este mes": "mes", "Este año": "anio", "Siempre": None}

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.es_admin = usuario is None or usuario.rol == "admin"
        self.c = colores_dashboard()
        self._datos_actuales = []
        self._ranking_actual = []
        self._marcados_actual = []

        self._construir_layout()
        self._cargar_resumen()

    # ------------------------------------------------------------
    def _construir_layout(self):
        # Toda la pantalla hace scroll (son varias tablas una debajo de
        # otra); las tablas internas son frames normales para no tener
        # scrolls anidados peleando por la rueda del mouse.
        contenedor = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        encabezado = ctk.CTkFrame(contenedor, fg_color="transparent")
        encabezado.pack(fill="x")

        crear_encabezado(
            encabezado, self.c,
            "Reportes",
            "Resumen del inventario y préstamos vencidos, listos para exportar."
        ).pack(side="left")

        botones = ctk.CTkFrame(encabezado, fg_color="transparent")
        botones.pack(side="right", anchor="e")

        ctk.CTkButton(botones, text="Actualizar", width=110,
                      command=self._cargar_resumen, **ESTILO_BOTON_SECUNDARIO).pack(side="left", padx=(0, 8))

        if self.es_admin:
            ctk.CTkButton(botones, text="Exportar CSV", width=120,
                          command=lambda: self._exportar(exportar_csv_secciones, ".csv"),
                          **ESTILO_BOTON_SECUNDARIO).pack(side="left", padx=(0, 8))
            ctk.CTkButton(botones, text="Exportar Excel", width=130,
                          command=lambda: self._exportar(exportar_excel_secciones, ".xlsx"),
                          **ESTILO_BOTON_PRIMARIO).pack(side="left", padx=(0, 8))
            ctk.CTkButton(botones, text="Exportar PDF", width=120,
                          command=lambda: self._exportar(exportar_pdf_secciones, ".pdf"),
                          **ESTILO_BOTON_PRIMARIO).pack(side="left")
        else:
            # Un usuario 'limitado' no puede descargar/exportar nada: solo
            # puede abrir el PDF para verlo, sin diálogo de "guardar como".
            ctk.CTkButton(botones, text="Ver PDF", width=120,
                          command=self._ver_pdf, **ESTILO_BOTON_PRIMARIO).pack(side="left")

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="x")

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(interior, text="Préstamos vencidos", font=("Segoe UI", 14, "bold"),
                     text_color=self.c["texto"]).pack(anchor="w", pady=(0, 8))

        crear_encabezado_tabla(
            interior, self.c,
            ["Código", "Artículo", "Alumno", "Devolución esperada"],
            self.ANCHOS
        )

        self.lista = ctk.CTkFrame(interior, fg_color="transparent")
        self.lista.pack(fill="both", expand=True)

        # Ranking de artículos más prestados, filtrable por día/mes/año.
        tarjeta_ranking = crear_card(contenedor, self.c)
        tarjeta_ranking.pack(fill="x", pady=(16, 0))

        interior_ranking = ctk.CTkFrame(tarjeta_ranking, fg_color="transparent")
        interior_ranking.pack(fill="both", expand=True, padx=14, pady=14)

        fila_titulo = ctk.CTkFrame(interior_ranking, fg_color="transparent")
        fila_titulo.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(fila_titulo, text="Artículos más prestados", font=("Segoe UI", 14, "bold"),
                     text_color=self.c["texto"]).pack(side="left")

        self.selector_periodo = ctk.CTkSegmentedButton(
            fila_titulo, values=list(self.PERIODOS.keys()),
            command=lambda _valor: self._cargar_ranking(),
            selected_color=COLORES["azul_primario"],
        )
        self.selector_periodo.set("Este mes")
        self.selector_periodo.pack(side="right")

        crear_encabezado_tabla(
            interior_ranking, self.c,
            ["#", "Código", "Artículo", "Categoría", "Veces prestado", "Unidades"],
            self.ANCHOS_RANKING
        )

        self.lista_ranking = ctk.CTkFrame(interior_ranking, fg_color="transparent")
        self.lista_ranking.pack(fill="both", expand=True)

        # Alumnos marcados (No cuida / Tardista / ambas).
        tarjeta_marcados = crear_card(contenedor, self.c)
        tarjeta_marcados.pack(fill="x", pady=(16, 0))

        interior_marcados = ctk.CTkFrame(tarjeta_marcados, fg_color="transparent")
        interior_marcados.pack(fill="both", expand=True, padx=14, pady=14)

        fila_titulo_marcados = ctk.CTkFrame(interior_marcados, fg_color="transparent")
        fila_titulo_marcados.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(fila_titulo_marcados, text="Alumnos marcados", font=("Segoe UI", 14, "bold"),
                     text_color=self.c["texto"]).pack(side="left")
        ctk.CTkLabel(
            fila_titulo_marcados,
            text=f"No cuida: {DANOS_PARA_NO_CUIDA}+ devoluciones dañadas  ·  "
                 f"Tardista: {TARDANZAS_PARA_TARDISTA}+ tardanzas",
            font=("Segoe UI", 11), text_color=self.c["subtext"],
        ).pack(side="right")

        crear_encabezado_tabla(
            interior_marcados, self.c,
            ["Alumno", "Sección", "Correo", "Daños", "Tardanzas", "Marca"],
            self.ANCHOS_MARCADOS
        )

        self.lista_marcados = ctk.CTkFrame(interior_marcados, fg_color="transparent")
        self.lista_marcados.pack(fill="both", expand=True)

    def _cargar_marcados(self):
        for hijo in self.lista_marcados.winfo_children():
            hijo.destroy()

        self._marcados_actual = alumnos_marcados()
        for alumno in self._marcados_actual:
            fondo, texto_color = (COLORES[k] for k in self.COLORES_MARCA[alumno["marca"]])

            def _celda_marca(celda, marca=alumno["marca"], fondo=fondo, texto_color=texto_color):
                crear_badge(celda, marca, fondo, texto_color).place(relx=0, rely=0.5, anchor="w")

            crear_fila_tabla(
                self.lista_marcados, self.c,
                [
                    alumno["nombre"],
                    f"{alumno['seccion']} {alumno['anio']}",
                    alumno["correo"],
                    str(alumno["danos"]),
                    str(alumno["tardanzas"]),
                    _celda_marca,
                ],
                self.ANCHOS_MARCADOS,
            )

        if not self._marcados_actual:
            ctk.CTkLabel(self.lista_marcados, text="No hay alumnos marcados.",
                         text_color=self.c["subtext"], font=("Segoe UI", 12)).pack(pady=20)

    def _cargar_ranking(self):
        for hijo in self.lista_ranking.winfo_children():
            hijo.destroy()

        texto_periodo = self.selector_periodo.get()
        filas = articulos_mas_prestados(limite=10, periodo=self.PERIODOS[texto_periodo])
        self._ranking_actual = filas
        for posicion, fila in enumerate(filas, start=1):
            crear_fila_tabla(
                self.lista_ranking, self.c,
                [
                    str(posicion),
                    fila["codigo_inventario"],
                    fila["nombre"],
                    fila["categoria"] or "—",
                    str(fila["veces_prestado"]),
                    str(int(fila["unidades"] or 0)),
                ],
                self.ANCHOS_RANKING,
            )

        if not filas:
            ctk.CTkLabel(self.lista_ranking,
                         text=f"No hay préstamos registrados ({texto_periodo.lower()}).",
                         text_color=self.c["subtext"], font=("Segoe UI", 12)).pack(pady=20)

    def _actualizar_kpis(self, resumen):
        for hijo in self.fila_kpis.winfo_children():
            hijo.destroy()

        disponibles = resumen.get("disponible", 0)
        prestados = resumen.get("prestado", 0)
        de_baja = resumen.get("de_baja", 0)

        datos = [
            (disponibles + prestados + de_baja, "Total de equipos", COLORES["azul_primario"]),
            (disponibles, "Disponibles", COLORES["disponible_texto"]),
            (prestados,   "Prestados",   COLORES["danado_texto"]),
            (de_baja,     "De baja",     COLORES["de_baja_texto"]),
        ]

        for numero, titulo, acento in datos:
            crear_kpi_card(self.fila_kpis, self.c, numero, titulo, acento).pack(
                side="left", expand=True, fill="both", padx=(0, 12)
            )

    # ------------------------------------------------------------
    def _cargar_resumen(self):
        resumen = {fila["estado"]: fila["cantidad"] for fila in resumen_articulos_por_estado()}
        self._actualizar_kpis(resumen)

        for hijo in self.lista.winfo_children():
            hijo.destroy()

        self._datos_actuales = prestamos_vencidos()
        for fila in self._datos_actuales:
            crear_fila_tabla(
                self.lista, self.c,
                [
                    fila["codigo_inventario"],
                    fila["articulo_nombre"],
                    fila["nombre_completo"],
                    fila["hora_estimada_devolucion"].strftime("%Y-%m-%d %H:%M"),
                ],
                self.ANCHOS,
            )

        if not self._datos_actuales:
            ctk.CTkLabel(self.lista, text="No hay préstamos vencidos.",
                         text_color=self.c["subtext"], font=("Segoe UI", 12)).pack(pady=20)

        self._cargar_ranking()
        self._cargar_marcados()

    def _secciones_reporte(self):
        """Lo que se exporta: préstamos vencidos, el ranking de más
        prestados del periodo elegido en pantalla y los alumnos marcados."""
        ranking = [
            {
                "#": posicion,
                "Código": fila["codigo_inventario"],
                "Artículo": fila["nombre"],
                "Categoría": fila["categoria"] or "",
                "Veces prestado": fila["veces_prestado"],
                "Unidades": int(fila["unidades"] or 0),
            }
            for posicion, fila in enumerate(self._ranking_actual, start=1)
        ]
        return [
            ("Préstamos vencidos", self._datos_actuales),
            (f"Más prestados ({self.selector_periodo.get()})", ranking),
            ("Alumnos marcados", [
                {
                    "Alumno": a["nombre"],
                    "Sección": f"{a['seccion']} {a['anio']}",
                    "Correo": a["correo"],
                    "Daños": a["danos"],
                    "Tardanzas": a["tardanzas"],
                    "Marca": a["marca"],
                }
                for a in self._marcados_actual
            ]),
        ]

    def _exportar(self, funcion_exportar, extension):
        if not (self._datos_actuales or self._ranking_actual or self._marcados_actual):
            messagebox.showwarning("Aviso", "No hay datos para exportar.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=extension)
        if not ruta:
            return
        try:
            funcion_exportar(self._secciones_reporte(), ruta)
            messagebox.showinfo("Éxito", f"Reporte exportado a:\n{ruta}")
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo exportar:\n{error}")

    def _ver_pdf(self):
        """Para el rol 'limitado': genera el PDF en un archivo temporal y
        lo abre con el visor de PDF de Windows, sin pasar por un diálogo
        de "guardar como" (no es una descarga/exportación)."""
        if not (self._datos_actuales or self._ranking_actual or self._marcados_actual):
            messagebox.showwarning("Aviso", "No hay datos para mostrar.")
            return

        ruta_temporal = os.path.join(tempfile.gettempdir(), "sigito_reporte.pdf")
        try:
            exportar_pdf_secciones(self._secciones_reporte(), ruta_temporal)
            abrir_archivo(ruta_temporal)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo mostrar el PDF:\n{error}")
