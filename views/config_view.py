"""
views/config_view.py — Pantalla de Configuración.

Frame embebido en el área de contenido del Dashboard (igual que
inventario/asignaciones/reportes/usuarios). Organizada en pestañas
(CTkTabview) — cada una es autocontenida, arma su(s) card(s) sobre
self._contenedor (ver _card()):

  - Contraseña — cambia la contraseña del usuario con sesión activa. Si
    es admin, pide su propia contraseña actual
    (controllers/auth_controller.cambiar_password); si es 'limitado',
    en vez de su contraseña actual pide la de un admin como
    autorización (controllers/auth_controller.cambiar_password_autorizado_por_admin).
    Es la ÚNICA pestaña que ve un usuario 'limitado' (sin tabview,
    solo esa tarjeta); todo lo demás es exclusivo de admin.
  - Correo — remitente + contraseña de aplicación (SMTP) + correo de
    copia al administrador. Guarda en la tabla `configuracion` vía
    controllers/config_controller.py. Incluye "Enviar correo de prueba".
  - Usuarios — crea usuarios de login nuevos (admin o limitado) y
    permite restablecer contraseña/activar/desactivar/eliminar
    (controllers/auth_controller.agregar_usuario y compañía).
  - Base de datos — exportar/cargar el inventario (CSV/Excel/ZIP con
    fotos), respaldo automático periódico (utils/respaldo.py), y la
    Zona de peligro que borra toda la BD operativa excepto usuarios
    (controllers/config_controller.reiniciar_base_datos), con doble
    confirmación y contraseña.
  - Recuperación — código de recuperación local, correo de recuperación
    propio, y el contacto de soporte que ve un usuario 'limitado' sin
    forma de recuperar su cuenta solo.
  - Diagnóstico — corre utils/diagnostico.ejecutar_diagnostico() y
    muestra ✓/✗ por cada pieza crítica del sistema.
"""

import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import crear_card, crear_encabezado, crear_campo_password
from controllers import auth_controller, config_controller
from controllers.inventario_controller import importar_articulos, datos_para_exportar
from utils import diagnostico
from utils.exportador import (
    exportar_csv, exportar_excel, importar_csv, importar_excel,
    exportar_inventario_zip, importar_inventario_zip,
)
from views.inventario_view import CARPETA_FOTOS


class ConfigView(ctk.CTkScrollableFrame):

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.es_admin = usuario is None or usuario.rol == "admin"
        self.c = colores_dashboard()
        self._contenedor = self  # _card() empaca aquí; cada pestaña lo redirige

        crear_encabezado(
            self, self.c,
            "Configuración",
            "Correo de avisos, contraseña de acceso y diagnóstico del sistema."
            if self.es_admin else "Cambiar tu contraseña de acceso."
        ).pack(anchor="w", padx=4, pady=(4, 16))

        if not self.es_admin:
            # Un usuario 'limitado' solo puede cambiar su contraseña (y
            # necesita que un admin la autorice) — no hace falta tabview
            # para una sola tarjeta.
            self._seccion_password()
            return

        self.tabview = ctk.CTkTabview(
            self, fg_color="transparent",
            segmented_button_fg_color=self.c["card"],
            segmented_button_selected_color=COLORES["azul_primario"],
            segmented_button_selected_hover_color=COLORES["azul_primario"],
            segmented_button_unselected_color=self.c["card"],
            text_color=self.c["texto"],
        )
        self.tabview.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        self._contenedor = self.tabview.add("Contraseña")
        self._seccion_password()

        self._contenedor = self.tabview.add("Correo")
        self._seccion_correo()

        self._contenedor = self.tabview.add("Usuarios")
        self._seccion_agregar_usuario()

        self._contenedor = self.tabview.add("Base de datos")
        self._seccion_exportar_inventario()
        self._seccion_respaldo_automatico()
        self._seccion_zona_peligro()

        self._contenedor = self.tabview.add("Recuperación")
        self._seccion_recuperacion_cuenta()

        self._contenedor = self.tabview.add("Diagnóstico")
        self._seccion_diagnostico()

        self.tabview.set("Contraseña")

    # ------------------------------------------------------------------
    # Helpers de layout
    # ------------------------------------------------------------------

    def _card(self, titulo, descripcion):
        tarjeta = crear_card(self._contenedor, self.c)
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

    def _campo_password(self, padre, etiqueta, **kwargs):
        ctk.CTkLabel(
            padre, text=etiqueta, anchor="w", font=("Segoe UI", 12),
            text_color=self.c["texto"],
        ).pack(fill="x", pady=(6, 2))
        frame, entry = crear_campo_password(padre, self.c, height=36, corner_radius=8, **kwargs)
        frame.pack(fill="x")
        return entry

    # ------------------------------------------------------------------
    # 2. Correo de avisos
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
        self.entry_smtp_pass = self._campo_password(
            interior,
            "Contraseña de aplicación" + ("  (ya guardada — escribe para reemplazar)" if tiene_pass else ""),
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
    # 1. Contraseña de login
    # ------------------------------------------------------------------

    def _seccion_password(self):
        descripcion = (
            "Cambia la contraseña con la que inicias sesión en SIGITO. "
            f"Mínimo {auth_controller.LONGITUD_MINIMA_PASSWORD} caracteres."
        )
        if not self.es_admin:
            descripcion += (
                " Por seguridad, en vez de tu contraseña actual necesitas que "
                "un administrador autorice el cambio escribiendo la suya."
            )
        interior = self._card("Contraseña de acceso", descripcion)

        if not self.usuario:
            ctk.CTkLabel(
                interior, text="No hay una sesión activa para cambiar la contraseña.",
                text_color=self.c["subtext"], font=("Segoe UI", 12),
            ).pack(anchor="w")
            return

        etiqueta_actual = "Contraseña actual" if self.es_admin else "Contraseña de un administrador"
        self.entry_pass_actual = self._campo_password(interior, etiqueta_actual)
        self.entry_pass_nueva = self._campo_password(interior, "Nueva contraseña")
        self.entry_pass_confirmar = self._campo_password(interior, "Confirmar nueva contraseña")

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
            if self.es_admin:
                auth_controller.cambiar_password(
                    usuario_id=self.usuario.id,
                    actual=self.entry_pass_actual.get(),
                    nueva=self.entry_pass_nueva.get(),
                    confirmar=self.entry_pass_confirmar.get(),
                )
            else:
                auth_controller.cambiar_password_autorizado_por_admin(
                    usuario_id=self.usuario.id,
                    password_admin=self.entry_pass_actual.get(),
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
    # 3. Exportar inventario
    # ------------------------------------------------------------------

    def _seccion_exportar_inventario(self):
        interior = self._card(
            "Descargar base de datos del inventario",
            "Descarga en un archivo todos los artículos registrados en el "
            "sistema hasta este momento (código, nombre, categoría, marca, "
            "modelo, serie, estado, stock, ubicación, fecha de adquisición)."
        )

        botones = ctk.CTkFrame(interior, fg_color="transparent")
        botones.pack(fill="x")

        ctk.CTkButton(
            botones, text="Descargar CSV", width=150, height=36,
            command=lambda: self._descargar_inventario(exportar_csv, ".csv"),
            **ESTILO_BOTON_SECUNDARIO,
        ).pack(side="left")

        ctk.CTkButton(
            botones, text="Descargar Excel", width=150, height=36,
            command=lambda: self._descargar_inventario(exportar_excel, ".xlsx"),
            **ESTILO_BOTON_PRIMARIO,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            botones, text="Descargar con fotos (.zip)", width=190, height=36,
            command=self._descargar_inventario_zip, **ESTILO_BOTON_SECUNDARIO,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            botones, text="Cargar inventario...", width=160, height=36,
            command=self._cargar_inventario_desde_archivo, **ESTILO_BOTON_SECUNDARIO,
        ).pack(side="left", padx=(10, 0))

        self.lbl_export_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_export_estado.pack(fill="x", pady=(10, 0))

    def _descargar_inventario(self, funcion_exportar, extension):
        datos = datos_para_exportar()
        if not datos:
            messagebox.showwarning("Aviso", "No hay artículos en el inventario para descargar.")
            return

        ruta = filedialog.asksaveasfilename(
            title="Descargar inventario",
            defaultextension=extension,
            initialfile=f"inventario{extension}",
        )
        if not ruta:
            return

        try:
            funcion_exportar(datos, ruta)
        except Exception as error:  # noqa: BLE001
            self.lbl_export_estado.configure(
                text=f"No se pudo exportar: {error}", text_color=COLORES["error"])
            return

        self.lbl_export_estado.configure(
            text=f"Inventario descargado en:\n{ruta}", text_color=COLORES["exito"])

    def _descargar_inventario_zip(self):
        """Igual que _descargar_inventario, pero además copia las fotos de
        cada artículo dentro del .zip, para llevarlas a otra instalación
        de SIGITO junto con los datos."""
        datos = datos_para_exportar(incluir_foto_path=True)
        if not datos:
            messagebox.showwarning("Aviso", "No hay artículos en el inventario para descargar.")
            return

        ruta = filedialog.asksaveasfilename(
            title="Descargar inventario con fotos",
            defaultextension=".zip",
            initialfile="inventario_con_fotos.zip",
            filetypes=[("Archivo comprimido", "*.zip")],
        )
        if not ruta:
            return

        try:
            exportar_inventario_zip(datos, ruta)
        except Exception as error:  # noqa: BLE001
            self.lbl_export_estado.configure(
                text=f"No se pudo exportar: {error}", text_color=COLORES["error"])
            return

        self.lbl_export_estado.configure(
            text=f"Inventario (con fotos) descargado en:\n{ruta}", text_color=COLORES["exito"])

    def _cargar_inventario_desde_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Cargar inventario desde archivo",
            filetypes=[
                ("Inventario (CSV, Excel o ZIP con fotos)", "*.csv *.xlsx *.zip"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("ZIP con fotos", "*.zip"),
            ],
        )
        if not ruta:
            return

        if not messagebox.askyesno(
            "Cargar inventario",
            "Esto crea artículos nuevos y actualiza los que ya existan "
            "(comparando por código de inventario) con lo que traiga el "
            "archivo. ¿Continuar?"
        ):
            return

        try:
            if ruta.lower().endswith(".zip"):
                filas = importar_inventario_zip(ruta, CARPETA_FOTOS)
            elif ruta.lower().endswith(".xlsx"):
                filas = importar_excel(ruta)
            else:
                filas = importar_csv(ruta)
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{error}")
            return

        resultado = importar_articulos(filas)

        resumen = (
            f"{resultado['creados']} artículo(s) creado(s), "
            f"{resultado['actualizados']} actualizado(s)."
        )
        if resultado["errores"]:
            resumen += f"\n\n{len(resultado['errores'])} fila(s) con problemas:\n"
            resumen += "\n".join(resultado["errores"][:10])
            if len(resultado["errores"]) > 10:
                resumen += f"\n... y {len(resultado['errores']) - 10} más."
            self.lbl_export_estado.configure(text=resumen, text_color=COLORES["error"])
            messagebox.showwarning("Carga completada con errores", resumen)
        else:
            self.lbl_export_estado.configure(text=resumen, text_color=COLORES["exito"])
            messagebox.showinfo("Éxito", resumen)

    # ------------------------------------------------------------------
    # 4. Respaldo automático del inventario
    # ------------------------------------------------------------------

    def _seccion_respaldo_automatico(self):
        interior = self._card(
            "Respaldo automático del inventario",
            "Si lo activas, SIGITO genera solo un respaldo (igual al "
            "\"Descargar con fotos\") en la carpeta backups/ cada tantas "
            "horas, mientras la app esté abierta, y borra los respaldos "
            "más viejos para no acumular espacio indefinidamente (guarda "
            "los últimos 10)."
        )

        try:
            ajuste = config_controller.obtener_ajuste_respaldo()
        except Exception as error:  # noqa: BLE001
            ctk.CTkLabel(
                interior, text=f"No se pudo leer el ajuste: {error}",
                text_color=COLORES["error"], font=("Segoe UI", 12),
            ).pack(anchor="w")
            return

        fila = ctk.CTkFrame(interior, fg_color="transparent")
        fila.pack(fill="x")

        self.switch_respaldo = ctk.CTkSwitch(
            fila, text="Activar respaldo automático",
            text_color=self.c["texto"], font=("Segoe UI", 12),
            progress_color=COLORES["azul_primario"],
        )
        if ajuste["activo"]:
            self.switch_respaldo.select()
        self.switch_respaldo.pack(side="left")

        ctk.CTkLabel(
            fila, text="cada", text_color=self.c["subtext"], font=("Segoe UI", 12),
        ).pack(side="left", padx=(18, 6))

        self.entry_intervalo_respaldo = ctk.CTkEntry(fila, width=60)
        self.entry_intervalo_respaldo.insert(0, str(ajuste["intervalo_horas"]))
        self.entry_intervalo_respaldo.pack(side="left")

        ctk.CTkLabel(
            fila, text="horas", text_color=self.c["subtext"], font=("Segoe UI", 12),
        ).pack(side="left", padx=(6, 18))

        ctk.CTkButton(
            fila, text="Guardar", width=100, height=32,
            command=self._guardar_ajuste_respaldo, **ESTILO_BOTON_PRIMARIO,
        ).pack(side="left")

        self.lbl_respaldo_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_respaldo_estado.pack(fill="x", pady=(10, 0))

    def _guardar_ajuste_respaldo(self):
        intervalo_texto = self.entry_intervalo_respaldo.get().strip()
        if not intervalo_texto.isdigit() or int(intervalo_texto) < 1:
            self.lbl_respaldo_estado.configure(
                text="El intervalo debe ser un número entero de 1 o más horas.",
                text_color=COLORES["error"])
            return

        config_controller.guardar_ajuste_respaldo(
            activo=bool(self.switch_respaldo.get()),
            intervalo_horas=int(intervalo_texto),
        )

        from utils import respaldo
        respaldo.iniciar()  # no hace nada si ya está corriendo; el hilo relee el ajuste solo

        self.lbl_respaldo_estado.configure(
            text="Ajuste de respaldo guardado.", text_color=COLORES["exito"])

    # ------------------------------------------------------------------
    # 5. Agregar usuario
    # ------------------------------------------------------------------

    def _seccion_agregar_usuario(self):
        interior = self._card(
            "Agregar usuario",
            "Crea un nuevo usuario de acceso a SIGITO. Rol «Admin»: acceso "
            "total. Rol «Limitado»: solo Inventario (código de barras y "
            "dar/revertir de baja), Asignaciones, Reportes (sin exportar, "
            "solo ver el PDF) y cambiar su propia contraseña (con "
            "autorización de un admin)."
        )

        fila = ctk.CTkFrame(interior, fg_color="transparent")
        fila.pack(fill="x")

        self.entry_nuevo_usuario_nombre = ctk.CTkEntry(fila, placeholder_text="Nombre completo")
        self.entry_nuevo_usuario_nombre.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.entry_nuevo_usuario_login = ctk.CTkEntry(fila, placeholder_text="Usuario (login)", width=150)
        self.entry_nuevo_usuario_login.pack(side="left", padx=6)

        frame_nuevo_usuario_password, self.entry_nuevo_usuario_password = crear_campo_password(
            fila, self.c, placeholder_text="Contraseña", width=140)
        frame_nuevo_usuario_password.pack(side="left", padx=6)

        self.combo_nuevo_usuario_rol = ctk.CTkComboBox(
            fila, values=["Limitado", "Admin"], state="readonly", width=110)
        self.combo_nuevo_usuario_rol.set("Limitado")
        self.combo_nuevo_usuario_rol.pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            interior, text="+ Agregar usuario", width=160, height=32,
            command=self._agregar_usuario, **ESTILO_BOTON_PRIMARIO,
        ).pack(anchor="w", pady=(10, 0))

        self.lbl_usuario_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_usuario_estado.pack(fill="x", pady=(8, 12))

        lista = ctk.CTkFrame(interior, fg_color="transparent")
        lista.pack(fill="x")
        self._lista_usuarios = lista
        self._recargar_lista_usuarios()

    def _recargar_lista_usuarios(self):
        for hijo in self._lista_usuarios.winfo_children():
            hijo.destroy()

        for u in auth_controller.listar_usuarios():
            fila = ctk.CTkFrame(self._lista_usuarios, fg_color=self.c["fila"], corner_radius=8, height=40)
            fila.pack(fill="x", pady=2)
            fila.pack_propagate(False)

            texto = f"{u['nombre']}  ·  {u['usuario']}  ·  {u['rol'].title()}"
            if not u["activo"]:
                texto += "  (inactivo)"

            ctk.CTkLabel(
                fila, text=texto, anchor="w", text_color=self.c["texto"], font=("Segoe UI", 12)
            ).pack(side="left", fill="both", expand=True, padx=(10, 0))

            # No mostrar acciones sobre el propio usuario con sesión activa
            # (para no poder desactivarse/eliminarse a sí mismo por error).
            if self.usuario and u["id"] == self.usuario.id:
                continue

            ctk.CTkButton(
                fila, text="Eliminar", width=70, height=26, corner_radius=8,
                font=("Segoe UI", 11, "bold"), fg_color="transparent",
                text_color=COLORES["error"], hover_color=self.c["card_inner"],
                command=lambda u=u: self._eliminar_usuario(u),
            ).pack(side="right", padx=(0, 8))

            texto_activo = "Desactivar" if u["activo"] else "Activar"
            ctk.CTkButton(
                fila, text=texto_activo, width=90, height=26, corner_radius=8,
                font=("Segoe UI", 11, "bold"), fg_color="transparent",
                text_color=self.c["subtext"], hover_color=self.c["card_inner"],
                command=lambda u=u: self._cambiar_estado_usuario(u),
            ).pack(side="right", padx=(0, 4))

            ctk.CTkButton(
                fila, text="Restablecer contraseña", width=170, height=26, corner_radius=8,
                font=("Segoe UI", 11, "bold"), fg_color="transparent",
                text_color=self.c["link"], hover_color=self.c["card_inner"],
                command=lambda u=u: self._restablecer_password_usuario(u),
            ).pack(side="right", padx=(0, 4))

    def _restablecer_password_usuario(self, usuario_fila):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Restablecer contraseña — {usuario_fila['usuario']}")
        ventana.geometry("340x220")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=14, pady=14)
        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            interior, text=f"Nueva contraseña para {usuario_fila['nombre']}",
            text_color=self.c["texto"], font=("Segoe UI", 12), wraplength=280, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        frame_entrada, entrada = crear_campo_password(interior, self.c)
        frame_entrada.pack(fill="x")
        entrada.focus_set()

        lbl_error = ctk.CTkLabel(interior, text="", text_color=COLORES["error"], font=("Segoe UI", 11))
        lbl_error.pack(anchor="w", pady=(6, 0))

        def _guardar():
            try:
                auth_controller.restablecer_password_admin(usuario_fila["id"], entrada.get())
            except ValueError as error:
                lbl_error.configure(text=str(error))
                return
            ventana.destroy()

        entrada.bind("<Return>", lambda _e: _guardar())
        ctk.CTkButton(
            interior, text="Restablecer", command=_guardar, **ESTILO_BOTON_PRIMARIO,
        ).pack(fill="x", pady=(14, 0))

    def _cambiar_estado_usuario(self, usuario_fila):
        nuevo_estado = not usuario_fila["activo"]
        verbo = "activar" if nuevo_estado else "desactivar"
        if not messagebox.askyesno("Confirmar", f"¿Quieres {verbo} a {usuario_fila['nombre']}?"):
            return
        try:
            auth_controller.cambiar_estado_usuario(usuario_fila["id"], nuevo_estado)
        except ValueError as error:
            messagebox.showerror("Error", str(error))
            return
        self._recargar_lista_usuarios()

    def _eliminar_usuario(self, usuario_fila):
        if not messagebox.askyesno(
            "Eliminar usuario",
            f"¿Eliminar a «{usuario_fila['nombre']}» de forma permanente?\n\n"
            "Esto solo funciona si el usuario nunca registró préstamos ni "
            "aparece en el historial. Si ya tiene actividad, desactívalo "
            "en su lugar."
        ):
            return
        try:
            auth_controller.eliminar_usuario(usuario_fila["id"])
        except ValueError as error:
            messagebox.showerror("No se pudo eliminar", str(error))
            return
        self._recargar_lista_usuarios()

    def _agregar_usuario(self):
        try:
            auth_controller.agregar_usuario(
                nombre=self.entry_nuevo_usuario_nombre.get(),
                usuario=self.entry_nuevo_usuario_login.get(),
                password=self.entry_nuevo_usuario_password.get(),
                rol=self.combo_nuevo_usuario_rol.get().lower(),
            )
        except ValueError as error:
            self.lbl_usuario_estado.configure(text=str(error), text_color=COLORES["error"])
            return
        except Exception as error:  # noqa: BLE001
            self.lbl_usuario_estado.configure(
                text=f"No se pudo crear el usuario: {error}", text_color=COLORES["error"])
            return

        for entry in (self.entry_nuevo_usuario_nombre, self.entry_nuevo_usuario_login,
                      self.entry_nuevo_usuario_password):
            entry.delete(0, "end")
        self.combo_nuevo_usuario_rol.set("Limitado")

        self.lbl_usuario_estado.configure(text="Usuario creado.", text_color=COLORES["exito"])
        self._recargar_lista_usuarios()

    # ------------------------------------------------------------------
    # 6. Recuperación de cuenta
    # ------------------------------------------------------------------

    def _seccion_recuperacion_cuenta(self):
        # --- Código de recuperación (tuyo, el admin con sesión activa) ---
        interior = self._card(
            "Código de recuperación",
            "Un código de respaldo para entrar si algún día olvidas tu "
            "contraseña, sin tener que tocar la base de datos a mano. "
            "Guárdalo en un lugar seguro (ej. un gestor de contraseñas): "
            "solo se muestra una vez, y usarlo lo invalida (hay que "
            "generar uno nuevo después)."
        )

        tiene_codigo = auth_controller.tiene_codigo_recuperacion(self.usuario.id) if self.usuario else False
        ctk.CTkLabel(
            interior,
            text="Ya tienes un código configurado." if tiene_codigo else "Todavía no tienes un código configurado.",
            text_color=self.c["subtext"], font=("Segoe UI", 12),
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkButton(
            interior, text="Regenerar código" if tiene_codigo else "Generar código",
            width=180, height=36, command=self._generar_codigo_recuperacion,
            **ESTILO_BOTON_PRIMARIO,
        ).pack(anchor="w")

        # --- Mi correo de recuperación ---
        interior_correo = self._card(
            "Mi correo de recuperación",
            "Si lo registras, también podrás recuperar tu contraseña "
            "pidiendo un código de un solo uso a este correo (además del "
            "código de recuperación de arriba). Requiere tener el correo "
            "de avisos (SMTP) configurado más arriba en esta pantalla."
        )
        self.entry_mi_correo_recuperacion = self._campo(
            interior_correo, "Correo", placeholder_text="tu_correo@ejemplo.com")
        if self.usuario and getattr(self.usuario, "correo", None):
            self.entry_mi_correo_recuperacion.insert(0, self.usuario.correo)

        ctk.CTkButton(
            interior_correo, text="Guardar correo", width=150, height=36,
            command=self._guardar_mi_correo_recuperacion, **ESTILO_BOTON_PRIMARIO,
        ).pack(anchor="w", pady=(10, 0))

        self.lbl_recuperacion_estado = ctk.CTkLabel(
            interior_correo, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_recuperacion_estado.pack(fill="x", pady=(8, 0))

        # --- Contacto de soporte (para usuarios 'limitado' sin forma de
        # recuperar su propia contraseña: se les muestra este contacto) ---
        interior_soporte = self._card(
            "Contacto de soporte",
            "Se les muestra a los usuarios con rol «Limitado» cuando "
            "intentan recuperar su contraseña y no tienen forma de "
            "hacerlo solos (ellos no generan código de recuperación)."
        )

        try:
            contacto = config_controller.obtener_contacto_soporte()
        except Exception as error:  # noqa: BLE001
            contacto = {"soporte_telefono": "", "soporte_coordinador": "", "soporte_correo": ""}
            ctk.CTkLabel(
                interior_soporte, text=f"No se pudo leer el contacto: {error}",
                text_color=COLORES["error"], font=("Segoe UI", 12),
            ).pack(anchor="w")

        fila_soporte = ctk.CTkFrame(interior_soporte, fg_color="transparent")
        fila_soporte.pack(fill="x")
        fila_soporte.grid_columnconfigure(0, weight=1, uniform="col")
        fila_soporte.grid_columnconfigure(1, weight=1, uniform="col")
        fila_soporte.grid_columnconfigure(2, weight=1, uniform="col")

        def _campo_soporte(columna, etiqueta, valor, placeholder):
            frame = ctk.CTkFrame(fila_soporte, fg_color="transparent")
            frame.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 6, 0))
            ctk.CTkLabel(frame, text=etiqueta, anchor="w", text_color=self.c["subtext"],
                         font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
            entrada = ctk.CTkEntry(frame, placeholder_text=placeholder)
            entrada.insert(0, valor)
            entrada.pack(fill="x")
            return entrada

        self.entry_soporte_telefono = _campo_soporte(
            0, "Teléfono", contacto["soporte_telefono"], "7712-0000")
        self.entry_soporte_coordinador = _campo_soporte(
            1, "Coordinador (nombre completo)", contacto["soporte_coordinador"], "Nombre Apellido")
        self.entry_soporte_correo = _campo_soporte(
            2, "Correo", contacto["soporte_correo"], "coordinador@institucion.edu")

        ctk.CTkButton(
            interior_soporte, text="Guardar contacto", width=150, height=36,
            command=self._guardar_contacto_soporte, **ESTILO_BOTON_PRIMARIO,
        ).pack(anchor="w", pady=(10, 0))

        self.lbl_soporte_estado = ctk.CTkLabel(
            interior_soporte, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_soporte_estado.pack(fill="x", pady=(8, 0))

    def _generar_codigo_recuperacion(self):
        codigo = auth_controller.generar_codigo_recuperacion(self.usuario.id)

        ventana = ctk.CTkToplevel(self)
        ventana.title("Tu código de recuperación")
        ventana.geometry("420x260")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)
        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            interior, text="Guárdalo ahora: no se volverá a mostrar.",
            text_color=COLORES["error"], font=("Segoe UI", 12, "bold"),
            wraplength=340, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        entrada_codigo = ctk.CTkEntry(interior, font=("Consolas", 16, "bold"), justify="center")
        entrada_codigo.insert(0, codigo)
        entrada_codigo.configure(state="readonly")
        entrada_codigo.pack(fill="x")

        def _copiar():
            self.clipboard_clear()
            self.clipboard_append(codigo)

        ctk.CTkButton(
            interior, text="Copiar", command=_copiar, **ESTILO_BOTON_SECUNDARIO,
        ).pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            interior, text="Ya lo guardé, cerrar", command=ventana.destroy,
            **ESTILO_BOTON_PRIMARIO,
        ).pack(fill="x", pady=(8, 0))

    def _guardar_mi_correo_recuperacion(self):
        try:
            auth_controller.actualizar_correo(self.usuario.id, self.entry_mi_correo_recuperacion.get())
        except ValueError as error:
            self.lbl_recuperacion_estado.configure(text=str(error), text_color=COLORES["error"])
            return
        self.lbl_recuperacion_estado.configure(text="Correo guardado.", text_color=COLORES["exito"])

    def _guardar_contacto_soporte(self):
        try:
            config_controller.guardar_contacto_soporte(
                telefono=self.entry_soporte_telefono.get(),
                coordinador=self.entry_soporte_coordinador.get(),
                correo=self.entry_soporte_correo.get(),
            )
        except ValueError as error:
            self.lbl_soporte_estado.configure(text=str(error), text_color=COLORES["error"])
            return
        self.lbl_soporte_estado.configure(text="Contacto guardado.", text_color=COLORES["exito"])

    # ------------------------------------------------------------------
    # 7. Zona de peligro — borrar toda la base de datos
    # ------------------------------------------------------------------

    def _seccion_zona_peligro(self):
        interior = self._card(
            "Zona de peligro",
            "Borra TODO el inventario, categorías, préstamos, historial de "
            "movimientos, mantenimientos, profesores autorizados y la "
            "configuración de correo. Los usuarios de acceso NO se borran, "
            "para que puedas seguir iniciando sesión después. Esta acción "
            "es irreversible."
        )

        if not self.usuario:
            ctk.CTkLabel(
                interior, text="No hay una sesión activa para autorizar esta acción.",
                text_color=self.c["subtext"], font=("Segoe UI", 12),
            ).pack(anchor="w")
            return

        ctk.CTkButton(
            interior, text="Borrar base de datos", width=200, height=36,
            fg_color=COLORES["error"], hover_color="#B91C1C", text_color="#FFFFFF",
            command=self._on_borrar_base_datos,
        ).pack(anchor="w")

        self.lbl_borrar_estado = ctk.CTkLabel(
            interior, text="", font=("Segoe UI", 12), anchor="w", justify="left",
        )
        self.lbl_borrar_estado.pack(fill="x", pady=(10, 0))

    def _on_borrar_base_datos(self):
        self._pedir_password_confirmacion(self._confirmar_borrado_paso1)

    def _pedir_password_confirmacion(self, al_confirmar):
        """Modal que pide la contraseña del usuario con sesión activa antes
        de dejar seguir con una acción destructiva."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Confirmar identidad")
        ventana.geometry("360x200")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=14, pady=14)
        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            interior, text="Escribe tu contraseña de inicio de sesión para continuar",
            text_color=self.c["texto"], font=("Segoe UI", 12), wraplength=280, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        frame_entrada_pass, entrada_pass = crear_campo_password(interior, self.c)
        frame_entrada_pass.pack(fill="x")
        entrada_pass.focus_set()

        lbl_error = ctk.CTkLabel(
            interior, text="", text_color=COLORES["error"], font=("Segoe UI", 11),
        )
        lbl_error.pack(anchor="w", pady=(6, 0))

        def _verificar():
            password = entrada_pass.get()
            if not password:
                lbl_error.configure(text="Escribe tu contraseña.")
                return
            if not auth_controller.verificar_password_usuario(self.usuario.id, password):
                lbl_error.configure(text="Contraseña incorrecta.")
                entrada_pass.delete(0, "end")
                return
            ventana.destroy()
            al_confirmar()

        entrada_pass.bind("<Return>", lambda _e: _verificar())

        botones = ctk.CTkFrame(interior, fg_color="transparent")
        botones.pack(fill="x", pady=(14, 0))
        ctk.CTkButton(
            botones, text="Cancelar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            botones, text="Continuar", command=_verificar, **ESTILO_BOTON_PRIMARIO,
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _confirmar_borrado_paso1(self):
        if not messagebox.askyesno(
            "¿Estás completamente seguro?",
            "Esto borrará TODO el inventario, categorías, préstamos, "
            "historial y configuración de correo. NO se puede deshacer.\n\n"
            "¿Quieres continuar?",
            icon="warning",
        ):
            return
        self._confirmar_borrado_paso2()

    def _confirmar_borrado_paso2(self):
        if not messagebox.askyesno(
            "Última confirmación",
            "Esta es tu última oportunidad para cancelar.\n\n"
            "¿Estás COMPLETAMENTE seguro de borrar toda la base de datos? "
            "Esta acción es irreversible.",
            icon="warning",
        ):
            return
        self._ejecutar_borrado()

    def _ejecutar_borrado(self):
        try:
            config_controller.reiniciar_base_datos()
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo borrar la base de datos:\n{error}")
            return

        self.lbl_borrar_estado.configure(
            text="Base de datos borrada. Tu usuario sigue activo.",
            text_color=COLORES["exito"],
        )
        messagebox.showinfo("Listo", "La base de datos fue borrada por completo.")

    # ------------------------------------------------------------------
    # 8. Diagnóstico
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
