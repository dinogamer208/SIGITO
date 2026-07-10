"""
views/reportes_view.py — Pantalla de reportes.

Responsable: Persona 5.

Qué debe hacer este archivo:
1. Mostrar resumen (artículos por estado, préstamos vencidos) usando
   controllers.reportes_controller.
2. Botón para exportar el reporte actual (PDF/Excel/CSV) usando
   utils/exportador.py.

Esqueleto:
"""

import tkinter as tk
from tkinter import ttk
# from controllers.reportes_controller import resumen_articulos_por_estado, prestamos_vencidos
# from utils.exportador import exportar_pdf, exportar_excel


class ReportesView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self._construir_widgets()

    def _construir_widgets(self):
        tk.Label(self, text="Reportes", font=("Arial", 14, "bold")).pack(pady=10)
        # TODO: mostrar resumen_articulos_por_estado() en un Treeview o labels
        tk.Button(self, text="Exportar PDF", command=self._on_exportar_pdf).pack(pady=5)

    def _on_exportar_pdf(self):
        raise NotImplementedError
