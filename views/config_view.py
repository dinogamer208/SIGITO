"""
views/config_view.py — Pantalla de Configuración.

Frame embebido en el área de contenido del Dashboard (igual que
inventario/asignaciones/reportes/usuarios). Tres apartados:

  1. Correo de avisos  — remitente + contraseña de aplicación (SMTP) +
     correo de copia al administrador. Guarda en la tabla `configuracion`
     vía controllers/config_controller.py. Incluye "Enviar correo de prueba".
  2. Contraseña de login — cambia la contraseña del usuario con sesión
     activa (controllers/auth_controller.cambiar_password).
  3. Diagnóstico — corre utils/diagnostico.ejecutar_diagnostico() y
     muestra ✓/✗ por cada pieza crítica del sistema.
"""

import threading

import customtkinter as ctk
from tkinter import messagebox

from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO
from views.componentes import crear_card, crear_encabezado
from controllers import auth_controller, config_controller
from utils import diagnostico


class ConfigView(ctk.CTkScrollableFrame):

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.c = colores_dashboard()

        crear_encabezado(
            self, self.c,
            "Configuración",
            "Correo de avisos, contraseña de acceso y diagnóstico del sistema."
        ).pack(anchor="w", padx=4, pady=(4, 16))

        self._seccion_correo()
        self._seccion_password()
        self._seccion_diagnostico()

    # ------------------------------------------------------------------
    # Helpers de layout
    # ------------------------------------------------------------------

    def _card(self, titulo, descripcion):
        tarjeta = crear_card(self, self.c)
        tarjeta.pack(fill="x", padx=4, pady=(0, 16))

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            interior, text=titulo, font=("Segoe UI", 15, "bold"),
            text_color=self.c["texto"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            interior, text=descripcion, font=("Segoe UI", 11),
            text_color=self.c["subtext"], justify="left", wraplength=560,
        ).pack(anchor="w", pady=(2, 12))

        return interior

    def _campo(self, padre, etiqueta, **kwargs):
        ctk.CTkLabel(
            padre, text=etiqueta, anchor="w", font=("Segoe UI", 12),
            text_color=self.c["texto"],
        ).pack(fill="x", pady=(6, 2))
        entry = ctk.CTkEntry(padre, height=36, corner_radius=8, **kwargs)
        entry.pack(fill="x")
        return entry

    # ------------------------------------------------------------------
    # 1. Correo de avisos
    # ------------------------------------------------------------------

    def _seccion_correo(self):
        interior = self._card(
            "Correo de avisos de atraso",
            "Cuenta de Gmail desde la que salen los correos a alumno y "
            "profesor cuando un préstamo se atrasa. La contraseña debe ser "
            "una «contraseña de aplicación» de Google, no la del correo. Se "
            "guarda cifrada y nunca se muestra de vuelta."
        )

        try:
            cfg = config_controller.obtener_config()
        except Exception as error:  # noqa: BLE001
            ctk.CTkLabel(
                interior, text=f"No se pudo leer la configuración: {error}",
                text_color=COLORES["error"], font=("Segoe UI", 12),
            ).pack(anchor="w")
            return

        self.entry_remitente = self._campo(
            interior, "Correo remitente", placeholder_text="avisos@gmail.com")
        self.entry_remitente.insert(0, cfg["correo_remitente"])

        tiene_pass = bool(cfg["smtp_app_password"])
        self.entry_smtp_pass = self._campo(
            interior,
            "Contraseña de aplicación" + ("  (ya guardada — escribe para reemplazar)" if tiene_pass else ""),
            show="*",
            placeholder_text="•••• •••• •••• ••••" if tiene_pass else "16 caracteres de Google",
        )

        self.entry_copia = self._campo(
            interior, "Correo de copia al administrador (opcional)",
            placeholder_text="admin@institucion.edu")
        self.entry_copia.insert(0, cfg["correo_copia_admin"])

        botones = ctk.CTkFrame(interior, fg_color="transparent")
        botones.pack(fill="x", pady=(14, 0))

        ctk.CTkButton(
            botones, text="Guardar", width=120, height=36,
            command=self._guardar_correo, **ESTILO_BOTON_PRIMARIO,
        ).pack(side="left")

        ctk.CTkButton(
            botones, text="Enviar correo de prueba", width=190, height=36,
            fg_color="transparent", border_width=1,
            border_color=self.c["borde"], text_color=self.c["texto"],
            hover_color=self.c["card_inner"],
            command=self._enviar_prueba,
        ).pack(side="left", padx=(10, 0))

        self.lbl_correo_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_correo_estado.pack(fill="x", pady=(10, 0))

    def _guardar_correo(self):
        nueva_pass = self.entry_smtp_pass.get()
        try:
            config_controller.guardar_config(
                correo_remitente=self.entry_remitente.get(),
                correo_copia_admin=self.entry_copia.get(),
                # cadena vacía = no tocar la contraseña ya guardada
                smtp_app_password=nueva_pass if nueva_pass else None,
            )
        except ValueError as error:
            self._estado_correo(str(error), ok=False)
            return
        except Exception as error:  # noqa: BLE001
            self._estado_correo(f"Error al guardar: {error}", ok=False)
            return

        self.entry_smtp_pass.delete(0, "end")
        self._estado_correo("Configuración guardada.", ok=True)

    def _enviar_prueba(self):
        self._estado_correo("Enviando correo de prueba…", ok=None)

        def tarea():
            try:
                destino = config_controller.enviar_correo_prueba()
                self.after(0, lambda: self._estado_correo(
                    f"Correo de prueba enviado a {destino}.", ok=True))
            except Exception as error:  # noqa: BLE001
                self.after(0, lambda err=error: self._estado_correo(
                    f"No se pudo enviar: {err}", ok=False))

        threading.Thread(target=tarea, daemon=True).start()

    def _estado_correo(self, texto, ok):
        color = {True: COLORES["exito"], False: COLORES["error"], None: self.c["subtext"]}[ok]
        self.lbl_correo_estado.configure(text=texto, text_color=color)

    # ------------------------------------------------------------------
    # 2. Contraseña de login
    # ------------------------------------------------------------------

    def _seccion_password(self):
        interior = self._card(
            "Contraseña de acceso",
            "Cambia la contraseña con la que inicias sesión en SIGITO. "
            f"Mínimo {auth_controller.LONGITUD_MINIMA_PASSWORD} caracteres."
        )

        if not self.usuario:
            ctk.CTkLabel(
                interior, text="No hay una sesión activa para cambiar la contraseña.",
                text_color=self.c["subtext"], font=("Segoe UI", 12),
            ).pack(anchor="w")
            return

        self.entry_pass_actual = self._campo(interior, "Contraseña actual", show="*")
        self.entry_pass_nueva = self._campo(interior, "Nueva contraseña", show="*")
        self.entry_pass_confirmar = self._campo(interior, "Confirmar nueva contraseña", show="*")

        ctk.CTkButton(
            interior, text="Cambiar contraseña", width=180, height=36,
            command=self._cambiar_password, **ESTILO_BOTON_PRIMARIO,
        ).pack(anchor="w", pady=(14, 0))

        self.lbl_pass_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_pass_estado.pack(fill="x", pady=(10, 0))

    def _cambiar_password(self):
        try:
            auth_controller.cambiar_password(
                usuario_id=self.usuario.id,
                actual=self.entry_pass_actual.get(),
                nueva=self.entry_pass_nueva.get(),
                confirmar=self.entry_pass_confirmar.get(),
            )
        except ValueError as error:
            self.lbl_pass_estado.configure(text=str(error), text_color=COLORES["error"])
            return
        except Exception as error:  # noqa: BLE001
            self.lbl_pass_estado.configure(
                text=f"Error al cambiar la contraseña: {error}", text_color=COLORES["error"])
            return

        for entry in (self.entry_pass_actual, self.entry_pass_nueva, self.entry_pass_confirmar):
            entry.delete(0, "end")
        self.lbl_pass_estado.configure(
            text="Contraseña actualizada. Se usará en el próximo inicio de sesión.",
            text_color=COLORES["exito"])

    # ------------------------------------------------------------------
    # 3. Diagnóstico
    # ------------------------------------------------------------------

    def _seccion_diagnostico(self):
        interior = self._card(
            "Diagnóstico del sistema",
            "Verifica que las piezas críticas responden: base de datos, "
            "hash de contraseñas, cifrado de credenciales y las consultas "
            "que alimentan el dashboard y los avisos."
        )

        self.boton_diag = ctk.CTkButton(
            interior, text="Ejecutar diagnóstico", width=180, height=36,
            command=self._ejecutar_diagnostico, **ESTILO_BOTON_PRIMARIO,
        )
        self.boton_diag.pack(anchor="w")

        self.contenedor_diag = ctk.CTkFrame(interior, fg_color="transparent")
        self.contenedor_diag.pack(fill="x", pady=(12, 0))

    def _ejecutar_diagnostico(self):
        self.boton_diag.configure(state="disabled", text="Ejecutando…")
        for hijo in self.contenedor_diag.winfo_children():
            hijo.destroy()

        def tarea():
            resultados = diagnostico.ejecutar_diagnostico()
            self.after(0, lambda: self._pintar_diagnostico(resultados))

        threading.Thread(target=tarea, daemon=True).start()

    def _pintar_diagnostico(self, resultados):
        self.boton_diag.configure(state="normal", text="Ejecutar diagnóstico")

        for r in resultados:
            fila = ctk.CTkFrame(self.contenedor_diag, fg_color=self.c["fila"],
                                corner_radius=8)
            fila.pack(fill="x", pady=3)

            icono = "✓" if r["ok"] else "✗"
            color = COLORES["exito"] if r["ok"] else COLORES["error"]

            ctk.CTkLabel(
                fila, text=icono, width=28, font=("Segoe UI", 14, "bold"),
                text_color=color,
            ).pack(side="left", padx=(10, 4), pady=8)

            texto = ctk.CTkFrame(fila, fg_color="transparent")
            texto.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(
                texto, text=r["nombre"], anchor="w", font=("Segoe UI", 12, "bold"),
                text_color=self.c["texto"],
            ).pack(anchor="w")
            ctk.CTkLabel(
                texto, text=r["detalle"], anchor="w", font=("Segoe UI", 10),
                text_color=self.c["subtext"], justify="left", wraplength=520,
            ).pack(anchor="w")

            ctk.CTkLabel(
                fila, text=f"{r['ms']} ms", width=64, font=("Segoe UI", 10),
                text_color=self.c["subtext"],
            ).pack(side="right", padx=10)

        total = len(resultados)
        ok = sum(1 for r in resultados if r["ok"])
        resumen = ctk.CTkLabel(
            self.contenedor_diag,
            text=f"{ok}/{total} chequeos correctos",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORES["exito"] if ok == total else COLORES["error"],
        )
        resumen.pack(anchor="w", pady=(8, 0))
