"""
views/usuarios_view.py — Gestión de profesores autorizados.

Ventana propia (antes vivía embebida dentro de dashboard_view._abrir_usuarios).
Sigue la misma lógica de clase que Dashboard: ctk.CTkToplevel que arma su
propio layout con los colores de views/tema.py.
"""

import customtkinter as ctk
from tkinter import messagebox

from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO
from views.componentes import crear_card, crear_encabezado, crear_encabezado_tabla, crear_fila_tabla
from controllers import auth_controller


class UsuariosView(ctk.CTkToplevel):

    ANCHOS = (180, 220, 140)

    def __init__(self, master):
        super().__init__(master)

        self.c = colores_dashboard()

        self.title("Profesores autorizados")
        self.geometry("620x560")
        self.minsize(560, 460)
        self.configure(fg_color=self.c["fondo"])

        self._construir_layout()
        self._cargar_profesores()

        self.transient(master)
        self.grab_set()

    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        crear_encabezado(
            contenedor, self.c,
            "Profesores autorizados",
            "Catálogo de profesores que pueden autorizar préstamos."
        ).pack(anchor="w", pady=(0, 14))

        self._crear_formulario(contenedor)

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True, pady=(14, 0))

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(interior, self.c, ["Nombre", "Correo", "Teléfono"], self.ANCHOS)

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

    def _crear_formulario(self, padre):
        tarjeta = crear_card(padre, self.c)
        tarjeta.pack(fill="x")

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="x", padx=14, pady=14)

        ctk.CTkLabel(interior, text="Nuevo profesor", font=("Segoe UI", 13, "bold"),
                     text_color=self.c["texto"]).pack(anchor="w", pady=(0, 8))

        fila = ctk.CTkFrame(interior, fg_color="transparent")
        fila.pack(fill="x")

        self.entry_nombre = ctk.CTkEntry(fila, placeholder_text="Nombre completo")
        self.entry_nombre.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.entry_correo = ctk.CTkEntry(fila, placeholder_text="Correo")
        self.entry_correo.pack(side="left", fill="x", expand=True, padx=6)

        self.entry_telefono = ctk.CTkEntry(fila, placeholder_text="Teléfono", width=120)
        self.entry_telefono.pack(side="left", padx=(6, 6))

        ctk.CTkButton(
            fila, text="+ Agregar", width=110, command=self._agregar_profesor,
            **ESTILO_BOTON_PRIMARIO
        ).pack(side="left", padx=(6, 0))

    def _cargar_profesores(self):
        for hijo in self.lista.winfo_children():
            hijo.destroy()

        for profesor in auth_controller.listar_profesores():
            crear_fila_tabla(
                self.lista, self.c,
                [profesor["nombre_completo"], profesor["correo"], profesor.get("telefono") or "—"],
                self.ANCHOS,
            )

    def _agregar_profesor(self):
        nombre = self.entry_nombre.get().strip()
        correo = self.entry_correo.get().strip()
        telefono = self.entry_telefono.get().strip() or None

        if not nombre or not correo:
            messagebox.showerror("Error", "Nombre y correo son obligatorios.")
            return

        auth_controller.agregar_profesor(nombre, correo, telefono)

        self.entry_nombre.delete(0, "end")
        self.entry_correo.delete(0, "end")
        self.entry_telefono.delete(0, "end")

        self._cargar_profesores()
