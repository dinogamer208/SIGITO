"""
views/asignacion_view.py — Pantalla de asignaciones.

Responsable: Persona 4.

Qué debe hacer este archivo:
1. Lista de asignaciones activas (Treeview) con botón "Registrar devolución".
2. Formulario para nuevo préstamo: elegir artículo disponible + usuario
   + fecha de devolución esperada.
3. Llama a controllers.asignacion_controller para toda la lógica.

Esqueleto:
"""

import tkinter as tk
from tkinter import ttk
# from controllers.asignacion_controller import (
#     listar_asignaciones_activas, registrar_prestamo, registrar_devolucion
# )


class AsignacionView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self._construir_widgets()
        self._cargar_asignaciones()

    def _construir_widgets(self):
        columnas = ("articulo", "usuario", "fecha_prestamo", "fecha_esperada")
        self.tree = ttk.Treeview(self, columns=columnas, show="headings")
        for col in columnas:
            self.tree.heading(col, text=col.replace("_", " ").title())
        self.tree.pack(fill="both", expand=True)
        tk.Button(self, text="Registrar devolución", command=self._on_devolucion).pack(pady=10)

    def _cargar_asignaciones(self):
        raise NotImplementedError

    def _on_devolucion(self):
        # TODO: tomar self.tree.selection(), convertir iid a int,
        # llamar a registrar_devolucion(id)
        raise NotImplementedError
