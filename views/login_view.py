"""
views/login_view.py — Pantalla de login.

Responsable: Persona 2.

Formulario de usuario/contraseña. Al iniciar sesión correctamente,
llama a on_login_exitoso(usuario) y se cierra a sí misma; main.py
decide qué hacer después (normalmente abrir el Dashboard).
"""

import queue
import threading

import customtkinter as ctk
from tkinter import messagebox

from controllers.auth_controller import iniciar_sesion
from views.tema import COLORES, color_fondo, color_card, color_texto, ESTILO_BOTON_PRIMARIO, forzar_redibujo


class LoginView(ctk.CTkToplevel):
    def __init__(self, master, on_login_exitoso=None):
        super().__init__(master)
        self.on_login_exitoso = on_login_exitoso
        self._login_en_curso = False

        self.update_idletasks()
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla  = self.winfo_screenheight()
        alto_util      = alto_pantalla - 48   # resta barra de tareas (~48px)

        self.title("SIGITO - Iniciar sesión")
        self.geometry(f"{ancho_pantalla}x{alto_util}+0+0")
        self.configure(fg_color=color_fondo())
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

        self._construir_widgets()
        forzar_redibujo(self)

    def _cerrar_aplicacion(self):
        self.master.destroy()

    def _construir_widgets(self):
        tarjeta = ctk.CTkFrame(
            self, fg_color=color_card(), corner_radius=16,
            border_width=1, border_color=COLORES["card_borde_oscuro"],
            width=380, height=420
        )
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")
        tarjeta.pack_propagate(False)

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
        if self._login_en_curso:
            return

        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get()

        if not usuario or not password:
            messagebox.showerror("Error", "Usuario y contraseña son obligatorios.")
            return

        self._login_en_curso = True
        self.boton_login.configure(state="disabled", text="Verificando...")

        # iniciar_sesion() tarda ~170 ms (bcrypt) y la primera vez arrastra
        # imports. Si corriera aquí mismo dejaría la ventana congelada todo
        # ese tiempo, así que va en un hilo. El resultado vuelve por una
        # queue que el hilo de Tk sondea con after() — llamar a after() /
        # widgets desde el hilo de trabajo no es seguro en Tkinter.
        cola = queue.Queue()

        def _trabajo():
            try:
                cola.put(("ok", iniciar_sesion(usuario, password)))
            except Exception as error:  # noqa: BLE001 - se muestra en la UI
                cola.put(("error", error))

        threading.Thread(target=_trabajo, daemon=True).start()
        self.after(100, self._revisar_login, cola)

    def _revisar_login(self, cola):
        try:
            tipo, valor = cola.get_nowait()
        except queue.Empty:
            self.after(100, self._revisar_login, cola)
            return

        if tipo == "error":
            self._login_error_conexion(valor)
        else:
            self._login_terminado(valor)

    def _restaurar_boton(self):
        self._login_en_curso = False
        self.boton_login.configure(state="normal", text="Iniciar sesión")

    def _login_error_conexion(self, error):
        messagebox.showerror("Error de conexión", f"No se pudo validar el login:\n{error}")
        self._restaurar_boton()

    def _login_terminado(self, usuario_autenticado):
        if usuario_autenticado is None:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")
            self._restaurar_boton()
            self.entry_password.delete(0, "end")
            return

        callback = self.on_login_exitoso
        self.destroy()
        if callback:
            callback(usuario_autenticado)
