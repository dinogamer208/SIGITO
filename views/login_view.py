"""
views/login_view.py — Pantalla de login.

Responsable: Persona 2.

Formulario de usuario/contraseña. Al iniciar sesión correctamente,
llama a on_login_exitoso(usuario) y se cierra a sí misma; main.py
decide qué hacer después (normalmente abrir el Dashboard).
"""

import customtkinter as ctk
from tkinter import messagebox

from controllers.auth_controller import iniciar_sesion
from views.tema import COLORES, color_fondo, color_card, color_texto, ESTILO_BOTON_PRIMARIO, forzar_redibujo


class LoginView(ctk.CTk):
    def __init__(self, on_login_exitoso=None):
        super().__init__()
        self.on_login_exitoso = on_login_exitoso

        self.title("SIGITO - Iniciar sesión")
        self.geometry("380x420")
        self.resizable(False, False)
        self.configure(fg_color=color_fondo())

        self._construir_widgets()
        forzar_redibujo(self)

    def _construir_widgets(self):
        tarjeta = ctk.CTkFrame(
            self, fg_color=color_card(), corner_radius=16,
            border_width=1, border_color=COLORES["card_borde_oscuro"]
        )
        tarjeta.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(
            tarjeta, text="SIGITO",
            font=("Segoe UI", 26, "bold"),
            text_color=color_texto()
        ).pack(pady=(30, 0))

        ctk.CTkLabel(
            tarjeta, text="Sistema de Gestión de Inventario",
            font=("Segoe UI", 12),
            text_color=COLORES["texto_sec_oscuro"]
        ).pack(pady=(0, 24))

        ctk.CTkLabel(tarjeta, text="Usuario", anchor="w",
                     text_color=color_texto()).pack(fill="x", padx=30)
        self.entry_usuario = ctk.CTkEntry(tarjeta, height=38, corner_radius=8)
        self.entry_usuario.pack(fill="x", padx=30, pady=(4, 16))

        ctk.CTkLabel(tarjeta, text="Contraseña", anchor="w",
                     text_color=color_texto()).pack(fill="x", padx=30)
        self.entry_password = ctk.CTkEntry(tarjeta, height=38, corner_radius=8, show="*")
        self.entry_password.pack(fill="x", padx=30, pady=(4, 24))
        self.entry_password.bind("<Return>", lambda _evento: self._on_login())

        self.boton_login = ctk.CTkButton(
            tarjeta, text="Iniciar sesión", height=40,
            command=self._on_login, **ESTILO_BOTON_PRIMARIO
        )
        self.boton_login.pack(fill="x", padx=30)

        self.entry_usuario.focus_set()

    def _on_login(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get()

        if not usuario or not password:
            messagebox.showerror("Error", "Usuario y contraseña son obligatorios.")
            return

        self.boton_login.configure(state="disabled", text="Verificando...")
        self.update_idletasks()

        try:
            usuario_autenticado = iniciar_sesion(usuario, password)
        except Exception as error:
            messagebox.showerror("Error de conexión", f"No se pudo validar el login:\n{error}")
            self.boton_login.configure(state="normal", text="Iniciar sesión")
            return

        if usuario_autenticado is None:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")
            self.boton_login.configure(state="normal", text="Iniciar sesión")
            self.entry_password.delete(0, "end")
            return

        callback = self.on_login_exitoso
        self.destroy()
        if callback:
            callback(usuario_autenticado)
