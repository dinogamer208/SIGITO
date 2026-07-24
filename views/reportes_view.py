"""
views/reportes_view.py — Pantalla de reportes.

Ventana propia (ctk.CTkToplevel), misma lógica de clase que Dashboard:
arma su layout con los colores de views/tema.py y los componentes
compartidos de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from controllers.reportes_controller import resumen_articulos_por_estado, prestamos_vencidos
from utils.exportador import exportar_excel, exportar_pdf, exportar_csv
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import crear_card, crear_encabezado, crear_kpi_card, crear_encabezado_tabla, crear_fila_tabla


class ReportesView(ctk.CTkToplevel):

    ANCHOS = (110, 220, 200, 170)

    def __init__(self, master):
        super().__init__(master)

        self.c = colores_dashboard()
        self._datos_actuales = []

        self.title("Reportes")
        self.geometry("920x640")
        self.minsize(760, 520)
        self.configure(fg_color=self.c["fondo"])

        self._construir_layout()
        self._cargar_resumen()

        self.transient(master)
        self.grab_set()

    # ------------------------------------------------------------
    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
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
        ctk.CTkButton(botones, text="Exportar CSV", width=120,
                      command=lambda: self._exportar(exportar_csv, ".csv"),
                      **ESTILO_BOTON_SECUNDARIO).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botones, text="Exportar Excel", width=130,
                      command=lambda: self._exportar(exportar_excel, ".xlsx"),
                      **ESTILO_BOTON_PRIMARIO).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botones, text="Exportar PDF", width=120,
                      command=lambda: self._exportar(exportar_pdf, ".pdf"),
                      **ESTILO_BOTON_PRIMARIO).pack(side="left")

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(interior, text="Préstamos vencidos", font=("Segoe UI", 14, "bold"),
                     text_color=self.c["texto"]).pack(anchor="w", pady=(0, 8))

        crear_encabezado_tabla(
            interior, self.c,
            ["Código", "Artículo", "Alumno", "Devolución esperada"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

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

    def _exportar(self, funcion_exportar, extension):
        if not self._datos_actuales:
            messagebox.showwarning("Aviso", "No hay préstamos vencidos para exportar.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=extension)
        if not ruta:
            return
        try:
            funcion_exportar(self._datos_actuales, ruta)
            messagebox.showinfo("Éxito", f"Reporte exportado a:\n{ruta}")
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo exportar:\n{error}")
