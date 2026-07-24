"""
views/main_menu_view.py — Menú principal (vista compartida).

Responsable: definir estructura entre las 5 personas de código; cada
quien conecta su botón a su propia vista.

Qué debe hacer este archivo:
1. Mostrar botones/pestañas de navegación según el rol del usuario
   (ej. un profesor no ve "Administrar usuarios").
2. Botones mínimos: Inventario, Asignaciones, Reportes, Cerrar sesión.

Esqueleto:
"""

"""
Nota: la pantalla principal real en uso es dashboard_view.Dashboard
(interfaz CustomTkinter con KPIs y gráficos). Esta vista se conserva
como menú simple/alternativo descrito en el README, funcional pero
sin usarse en el flujo por defecto de main.py.
"""

import tkinter as tk
from views.inventario_view import InventarioView
from views.asignacion_view import AsignacionView
from views.reportes_view import ReportesView
from controllers.auth_controller import cerrar_sesion


class MainMenuView(tk.Frame):
    def __init__(self, master, usuario):
        super().__init__(master)
        self.master = master
        self.usuario = usuario
        self.pack(fill="both", expand=True)
        self._construir_widgets()

    def _construir_widgets(self):
        tk.Label(self, text=f"Bienvenido/a, {self.usuario.nombre}").pack(pady=10)

        tk.Button(self, text="Inventario", command=self._abrir_inventario).pack(fill="x")
        tk.Button(self, text="Asignaciones", command=self._abrir_asignaciones).pack(fill="x")
        tk.Button(self, text="Reportes", command=self._abrir_reportes).pack(fill="x")
        tk.Button(self, text="Cerrar sesión", command=self._cerrar_sesion).pack(fill="x", pady=(20, 0))

    def _abrir_inventario(self):
        InventarioView(self)

    def _abrir_asignaciones(self):
        AsignacionView(self, usuario=self.usuario)

    def _abrir_reportes(self):
        ReportesView(self)

    def _cerrar_sesion(self):
        cerrar_sesion()
        self.master.destroy()
