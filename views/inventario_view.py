"""
views/inventario_view.py — Pantalla de inventario.

Responsable: Persona 3.

Qué debe hacer este archivo:
1. Treeview con la lista de artículos (llamar a
   controllers.inventario_controller.listar_articulos()).
2. Formulario para agregar/editar artículo, y botón para escanear/
   ingresar código de barras.
3. Recordar: los iid del Treeview son strings; convertir a int antes
   de mandarlos al controller.

Esqueleto:
"""

import tkinter as tk
from tkinter import ttk
# from controllers.inventario_controller import listar_articulos, crear_articulo


class InventarioView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self._construir_widgets()
        self._cargar_articulos()

    def _construir_widgets(self):
        columnas = ("codigo_barras", "nombre", "estado")
        self.tree = ttk.Treeview(self, columns=columnas, show="headings")
        for col in columnas:
            self.tree.heading(col, text=col.replace("_", " ").title())
        self.tree.pack(fill="both", expand=True)
        # TODO: botones Agregar / Editar / Eliminar

    def _cargar_articulos(self):
        # TODO: limpiar tree, llamar a listar_articulos() y hacer
        # self.tree.insert("", "end", iid=str(a.id), values=(...))
        raise NotImplementedError
