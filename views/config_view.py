"""
views/config_view.py — Pantalla de Configuración.

Frame embebido en el área de contenido del Dashboard (igual que
inventario/asignaciones/reportes/usuarios). Tres apartados:

  1. Correo de avisos  — remitente + contraseña de aplicación (SMTP) +
     correo de copia al administrador. Guarda en la tabla `configuracion`
     vía controllers/config_controller.py. Incluye "Enviar correo de prueba".
  2. Contraseña de login — cambia la contraseña del usuario con sesión
     activa (controllers/auth_controller.cambiar_password).
  3. Exportar inventario — descarga en CSV/Excel todos los artículos
     que tiene el sistema hasta ese momento, con su categoría resuelta.
  4. Zona de peligro — borra toda la base de datos operativa (inventario,
     préstamos, historial, profesores, config. de correo) excepto los
     usuarios de login. Pide la contraseña del usuario con sesión activa
     y una doble confirmación antes de ejecutar nada
     (controllers/config_controller.reiniciar_base_datos).
  5. Diagnóstico — corre utils/diagnostico.ejecutar_diagnostico() y
     muestra ✓/✗ por cada pieza crítica del sistema.
"""

import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import crear_card, crear_encabezado
from controllers import auth_controller, config_controller
from controllers.inventario_controller import listar_articulos, listar_categorias, importar_articulos
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
        self.c = colores_dashboard()

        crear_encabezado(
            self, self.c,
            "Configuración",
            "Correo de avisos, contraseña de acceso y diagnóstico del sistema."
        ).pack(anchor="w", padx=4, pady=(4, 16))

        self._seccion_correo()
        self._seccion_password()
        self._seccion_exportar_inventario()
        self._seccion_zona_peligro()
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
        articulos = listar_articulos()
        if not articulos:
            messagebox.showwarning("Aviso", "No hay artículos en el inventario para descargar.")
            return

        nombre_categoria = {cat["id"]: cat["nombre"] for cat in listar_categorias()}

        datos = [
            {
                "codigo_inventario": a.codigo_inventario,
                "nombre": a.nombre,
                "categoria": nombre_categoria.get(a.categoria_id, ""),
                "marca": a.marca or "",
                "modelo": a.modelo or "",
                "serie": a.serie or "",
                "estado_fisico": a.estado_fisico,
                "estado_disponibilidad": a.estado_disponibilidad,
                "cantidad_total": a.cantidad_total,
                "cantidad_disponible": a.cantidad_disponible,
                "ubicacion_actual": a.ubicacion_actual or "",
                "fecha_adquisicion": a.fecha_adquisicion,
            }
            for a in articulos
        ]

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
        import os

        articulos = listar_articulos()
        if not articulos:
            messagebox.showwarning("Aviso", "No hay artículos en el inventario para descargar.")
            return

        nombre_categoria = {cat["id"]: cat["nombre"] for cat in listar_categorias()}

        datos = [
            {
                "codigo_inventario": a.codigo_inventario,
                "nombre": a.nombre,
                "categoria": nombre_categoria.get(a.categoria_id, ""),
                "marca": a.marca or "",
                "modelo": a.modelo or "",
                "serie": a.serie or "",
                "estado_fisico": a.estado_fisico,
                "estado_disponibilidad": a.estado_disponibilidad,
                "cantidad_total": a.cantidad_total,
                "cantidad_disponible": a.cantidad_disponible,
                "ubicacion_actual": a.ubicacion_actual or "",
                "fecha_adquisicion": a.fecha_adquisicion,
                "foto_path": os.path.abspath(a.foto_path) if a.foto_path else "",
            }
            for a in articulos
        ]

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
    # 4. Zona de peligro — borrar toda la base de datos
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

        entrada_pass = ctk.CTkEntry(interior, show="*")
        entrada_pass.pack(fill="x")
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
    # 5. Diagnóstico
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
