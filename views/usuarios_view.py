"""
views/usuarios_view.py — Gestión de profesores autorizados.

Frame embebido dentro del área de contenido del Dashboard (se muestra
al navegar desde el sidebar, reemplazando la vista anterior). Arma su
propio layout con los colores de views/tema.py.
"""

import customtkinter as ctk
from tkinter import messagebox

from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO
from views.componentes import (
    crear_card, crear_encabezado, crear_encabezado_tabla, crear_fila_tabla, crear_badge, centrar_ventana
)
from utils.validaciones import correo_valido
from controllers import auth_controller


class UsuariosView(ctk.CTkFrame):

    ANCHOS = (200, 240, 140, 100)

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.c = colores_dashboard()

        self._construir_layout()
        self._cargar_profesores()

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

        crear_encabezado_tabla(interior, self.c, ["Nombre", "Correo", "Teléfono", "Estado"], self.ANCHOS)

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

        # Todos (también los inactivos, al final): un profesor no se borra
        # porque sus préstamos lo referencian; se desactiva y deja de
        # aparecer en "Profesor que autoriza" del Nuevo préstamo.
        profesores = sorted(auth_controller.listar_profesores(solo_activos=False),
                            key=lambda p: (not p["activo"], p["nombre_completo"].lower()))
        for profesor in profesores:
            activo = bool(profesor["activo"])
            fondo, color, texto = ((COLORES["disponible_fondo"], COLORES["disponible_texto"], "Activo") if activo
                                   else (COLORES["de_baja_fondo"], COLORES["de_baja_texto"], "Inactivo"))

            def _celda_estado(celda, fondo=fondo, color=color, texto=texto):
                crear_badge(celda, texto, fondo, color).place(relx=0, rely=0.5, anchor="w")

            crear_fila_tabla(
                self.lista, self.c,
                [profesor["nombre_completo"], profesor["correo"], profesor.get("telefono") or "—", _celda_estado],
                self.ANCHOS,
                acciones=[
                    ("Editar", lambda p=profesor: self._editar_profesor(p)),
                    ("Desactivar" if activo else "Activar", lambda p=profesor: self._cambiar_activo(p)),
                ],
            )

    def _cambiar_activo(self, profesor):
        activar = not profesor["activo"]
        if not activar and not messagebox.askyesno(
            "Desactivar profesor",
            f"¿Desactivar a {profesor['nombre_completo']}?\n\nYa no aparecerá para autorizar "
            "préstamos nuevos. Sus préstamos anteriores se conservan y puedes volver a activarlo."
        ):
            return
        auth_controller.editar_profesor(profesor["id"], profesor["nombre_completo"], profesor["correo"],
                                        profesor.get("telefono"), activo=activar)
        self._cargar_profesores()

    def _editar_profesor(self, profesor):
        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Editar profesor")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)
        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=20, pady=20)

        campos = {}
        for etiqueta, clave in (("Nombre completo", "nombre_completo"), ("Correo", "correo"),
                                ("Teléfono (opcional)", "telefono")):
            ctk.CTkLabel(interior, text=etiqueta, anchor="w", text_color=self.c["subtext"],
                         font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))
            entrada = ctk.CTkEntry(interior, width=340)
            entrada.insert(0, profesor.get(clave) or "")
            entrada.pack(fill="x")
            campos[clave] = entrada

        def _guardar():
            nombre = campos["nombre_completo"].get().strip()
            correo = campos["correo"].get().strip()
            telefono = campos["telefono"].get().strip() or None
            if not nombre or not correo:
                messagebox.showerror("Error", "Nombre y correo son obligatorios.", parent=ventana)
                return
            if not correo_valido(correo):
                messagebox.showerror("Error", "Correo inválido.", parent=ventana)
                return
            auth_controller.editar_profesor(profesor["id"], nombre, correo, telefono,
                                            activo=bool(profesor["activo"]))
            ventana.destroy()
            self._cargar_profesores()

        ctk.CTkButton(interior, text="Guardar cambios", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(16, 0))
        ctk.CTkButton(
            interior, text="Cancelar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"], hover_color=self.c["card_inner"],
        ).pack(fill="x", pady=(6, 0))
        ventana.bind("<Return>", lambda _e: _guardar())

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
