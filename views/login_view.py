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

from controllers import auth_controller, config_controller
from controllers.auth_controller import iniciar_sesion
from views.tema import (
    COLORES, color_fondo, color_card, color_texto, colores_dashboard,
    ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO, forzar_redibujo,
)
from views.componentes import crear_card, crear_campo_password, centrar_ventana


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
            width=380, height=460
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
        frame_password, self.entry_password = crear_campo_password(
            tarjeta, colores_dashboard(), height=38, corner_radius=8)
        frame_password.pack(fill="x", padx=30, pady=(4, 24))
        self.entry_password.bind("<Return>", lambda _evento: self._on_login())

        self.boton_login = ctk.CTkButton(
            tarjeta, text="Iniciar sesión", height=40,
            command=self._on_login, **ESTILO_BOTON_PRIMARIO
        )
        self.boton_login.pack(fill="x", padx=30)

        ctk.CTkButton(
            tarjeta, text="¿Olvidaste tu contraseña?", height=28,
            fg_color="transparent", hover_color=color_card(),
            text_color=COLORES["texto_sec_oscuro"], font=("Segoe UI", 11, "underline"),
            command=self._abrir_recuperacion,
        ).pack(fill="x", padx=30, pady=(10, 0))

        self.entry_usuario.focus_set()

    # ------------------------------------------------------------
    # Recuperación de cuenta (código local o correo; si ninguno está
    # disponible para ese usuario, se muestra el contacto de soporte).
    # ------------------------------------------------------------
    def _abrir_recuperacion(self):
        c = colores_dashboard()

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Recuperar contraseña")
        ventana.geometry("380x360")
        ventana.configure(fg_color=color_fondo())
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)
        contenido = ctk.CTkFrame(tarjeta, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=18, pady=18)

        estado = {"usuario": None}

        class _CambiarAContacto(Exception):
            """Señal interna: el flujo de código/correo debe cambiar a la
            pantalla de contacto de soporte en vez de mostrar un error."""

        def _limpiar():
            for hijo in contenido.winfo_children():
                hijo.destroy()

        def _ajustar_alto():
            ventana.update_idletasks()
            alto = tarjeta.winfo_reqheight() + 32
            ventana.geometry(f"380x{max(alto, 260)}")

        def _mostrar_contacto():
            _limpiar()
            ctk.CTkLabel(
                contenido, text="No hay forma de recuperar esta cuenta automáticamente.",
                text_color=c["texto"], font=("Segoe UI", 13, "bold"),
                wraplength=300, justify="left",
            ).pack(anchor="w", pady=(0, 10))

            try:
                contacto = config_controller.obtener_contacto_soporte()
            except Exception:
                contacto = {"soporte_telefono": "", "soporte_coordinador": "", "soporte_correo": ""}

            lineas = []
            if contacto.get("soporte_coordinador"):
                lineas.append(f"Coordinador: {contacto['soporte_coordinador']}")
            if contacto.get("soporte_telefono"):
                lineas.append(f"Teléfono: {contacto['soporte_telefono']}")
            if contacto.get("soporte_correo"):
                lineas.append(f"Correo: {contacto['soporte_correo']}")

            texto = "\n".join(lineas) if lineas else (
                "Comunícate con el administrador del sistema para que te "
                "restablezca la contraseña."
            )
            ctk.CTkLabel(
                contenido, text=texto, text_color=c["subtext"], font=("Segoe UI", 12),
                justify="left", wraplength=300,
            ).pack(anchor="w")

            ctk.CTkButton(
                contenido, text="Cerrar", command=ventana.destroy, **ESTILO_BOTON_SECUNDARIO,
            ).pack(fill="x", pady=(16, 0))
            _ajustar_alto()

        def _pantalla_inicial():
            _limpiar()
            ctk.CTkLabel(
                contenido, text="Usuario", anchor="w", text_color=c["texto"], font=("Segoe UI", 12),
            ).pack(fill="x", pady=(0, 2))
            entrada_usuario = ctk.CTkEntry(contenido)
            entrada_usuario.pack(fill="x")
            entrada_usuario.focus_set()

            lbl_error = ctk.CTkLabel(contenido, text="", text_color=COLORES["error"], font=("Segoe UI", 11))
            lbl_error.pack(anchor="w", pady=(6, 0))

            def _con_codigo():
                usuario = entrada_usuario.get().strip()
                if not usuario:
                    lbl_error.configure(text="Escribe tu usuario.")
                    return
                estado["usuario"] = usuario
                _pantalla_codigo()

            def _con_correo():
                usuario = entrada_usuario.get().strip()
                if not usuario:
                    lbl_error.configure(text="Escribe tu usuario.")
                    return
                estado["usuario"] = usuario
                try:
                    correo_destino = auth_controller.solicitar_codigo_recuperacion_por_correo(usuario)
                except ValueError:
                    _mostrar_contacto()
                    return
                _pantalla_codigo_correo(correo_destino)

            ctk.CTkButton(
                contenido, text="Tengo un código de recuperación", height=34,
                command=_con_codigo, **ESTILO_BOTON_PRIMARIO,
            ).pack(fill="x", pady=(14, 8))
            ctk.CTkButton(
                contenido, text="Enviarme un código por correo", height=34,
                command=_con_correo, **ESTILO_BOTON_SECUNDARIO,
            ).pack(fill="x")
            _ajustar_alto()

        def _pantalla_restablecer(titulo, mensaje, on_confirmar):
            _limpiar()
            ctk.CTkLabel(
                contenido, text=titulo, text_color=c["texto"], font=("Segoe UI", 13, "bold"),
                wraplength=300, justify="left",
            ).pack(anchor="w", pady=(0, 4))
            if mensaje:
                ctk.CTkLabel(
                    contenido, text=mensaje, text_color=c["subtext"], font=("Segoe UI", 11),
                    wraplength=300, justify="left",
                ).pack(anchor="w", pady=(0, 10))

            ctk.CTkLabel(contenido, text="Código", anchor="w",
                         text_color=c["texto"], font=("Segoe UI", 12)).pack(fill="x", pady=(4, 2))
            entrada_codigo = ctk.CTkEntry(contenido)
            entrada_codigo.pack(fill="x")

            ctk.CTkLabel(contenido, text="Nueva contraseña", anchor="w",
                         text_color=c["texto"], font=("Segoe UI", 12)).pack(fill="x", pady=(8, 2))
            frame_nueva, entrada_nueva = crear_campo_password(contenido, c)
            frame_nueva.pack(fill="x")

            ctk.CTkLabel(contenido, text="Confirmar nueva contraseña", anchor="w",
                         text_color=c["texto"], font=("Segoe UI", 12)).pack(fill="x", pady=(8, 2))
            frame_confirmar, entrada_confirmar = crear_campo_password(contenido, c)
            frame_confirmar.pack(fill="x")

            lbl_error = ctk.CTkLabel(contenido, text="", text_color=COLORES["error"], font=("Segoe UI", 11))
            lbl_error.pack(anchor="w", pady=(6, 0))

            def _confirmar():
                try:
                    on_confirmar(entrada_codigo.get().strip(), entrada_nueva.get(), entrada_confirmar.get())
                except _CambiarAContacto:
                    _mostrar_contacto()
                    return
                except ValueError as error:
                    lbl_error.configure(text=str(error))
                    return
                messagebox.showinfo("Listo", "Contraseña restablecida. Ya puedes iniciar sesión.")
                ventana.destroy()

            ctk.CTkButton(
                contenido, text="Restablecer contraseña", command=_confirmar, **ESTILO_BOTON_PRIMARIO,
            ).pack(fill="x", pady=(12, 0))
            _ajustar_alto()

        def _pantalla_codigo():
            def _on_confirmar(codigo, nueva, confirmar):
                try:
                    auth_controller.recuperar_con_codigo(estado["usuario"], codigo, nueva, confirmar)
                except ValueError as error:
                    if "no tiene un código de recuperación configurado" in str(error):
                        raise _CambiarAContacto() from None
                    raise
            _pantalla_restablecer(
                "Código de recuperación",
                "El que generaste (o te dio el administrador) desde Configuración.",
                _on_confirmar,
            )

        def _pantalla_codigo_correo(correo_destino):
            def _on_confirmar(codigo, nueva, confirmar):
                auth_controller.recuperar_con_codigo_correo(estado["usuario"], codigo, nueva, confirmar)
            _pantalla_restablecer(
                "Revisa tu correo",
                f"Enviamos un código a {correo_destino}. Vence en 30 minutos.",
                _on_confirmar,
            )

        _pantalla_inicial()

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
