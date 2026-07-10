"""
views/login_view.py — Pantalla de login.

Responsable: Persona 2.

Qué debe hacer este archivo:
1. Formulario Tkinter con campos correo/contraseña y botón "Iniciar sesión".
2. Al enviar, llamar a controllers.auth_controller.iniciar_sesion(...).
3. Si es correcto -> cerrar esta ventana y abrir views/main_menu_view.py.
   Si falla -> mostrar mensaje de error (messagebox.showerror).

Esqueleto:
"""

import tkinter as tk
from tkinter import messagebox
# from controllers.auth_controller import iniciar_sesion
# from views.main_menu_view import MainMenuView


class LoginView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        self._construir_widgets()

    def _construir_widgets(self):
        tk.Label(self, text="Correo").pack(pady=(20, 0))
        self.entry_correo = tk.Entry(self)
        self.entry_correo.pack()

        tk.Label(self, text="Contraseña").pack(pady=(10, 0))
        self.entry_password = tk.Entry(self, show="*")
        self.entry_password.pack()

        tk.Button(self, text="Iniciar sesión", command=self._on_login).pack(pady=20)

    def _on_login(self):
        correo = self.entry_correo.get()
        password = self.entry_password.get()
        # TODO: usuario = iniciar_sesion(correo, password)
        # TODO: si usuario -> self.destroy(); MainMenuView(self.master, usuario)
        # TODO: si no -> messagebox.showerror("Error", "Credenciales inválidas")
        raise NotImplementedError
