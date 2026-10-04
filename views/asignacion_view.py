"""
views/asignacion_view.py — Pantalla de asignaciones (préstamos y devoluciones).

Frame embebido dentro del área de contenido del Dashboard (se muestra
al navegar desde el sidebar, reemplazando la vista anterior): arma su
layout con los colores de views/tema.py y los componentes compartidos
de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import os
import uuid
from datetime import date, timedelta

import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import Calendar
from PIL import Image

from controllers.asignacion_controller import (
    listar_asignaciones_activas, registrar_prestamo, registrar_devolucion,
    listar_devoluciones, historial_alumnos, historial_alumno, clave_alumno, buscar_alumnos,
    prestamos_activos_de_articulo, detalle_prestamo,
    extender_prestamo, historial_prestamos_alumno,
    MARCA_NO_CUIDA, MARCA_TARDISTA, MARCA_AMBAS,
    DANOS_PARA_NO_CUIDA, TARDANZAS_PARA_TARDISTA,
)
from controllers.inventario_controller import listar_articulos, buscar_articulo_por_codigo
from controllers.auth_controller import listar_profesores
from controllers.config_controller import leer_ajuste, guardar_ajuste
from controllers.mantenimiento_controller import (
    enviar_a_mantenimiento, marcar_regresado, listar_en_mantenimiento
)
from utils.validaciones import correo_valido
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card,
    crear_encabezado_tabla, crear_fila_tabla, crear_badge,
    abrir_ventana_camara, centrar_ventana, imagen_avatar
)

CARPETA_FOTOS_ALUMNOS = os.path.join("assets", "fotos_prestamos")
CARPETA_FOTOS_DEVOLUCIONES = os.path.join("assets", "fotos_devoluciones")


class AsignacionView(ctk.CTkFrame):

    # Sin columna "Salida" (se ve en el historial del alumno): con la
    # columna Artículo no cabían los botones Foto/Extender/Devolver.
    ANCHOS = (165, 165, 70, 45, 120, 80, 130)
    ANCHOS_DEVUELTOS = (160, 170, 130, 130, 100, 170)
    # Colores del badge de cada marca del alumno.
    COLORES_MARCA = {
        MARCA_NO_CUIDA: ("danado_fondo", "danado_texto"),
        MARCA_TARDISTA: ("tardista_fondo", "tardista_texto"),
        MARCA_AMBAS:    ("atrasado_fondo", "atrasado_texto"),
    }
    ANCHOS_MANTENIMIENTO = (200, 150, 200, 140)
    _COLORES_AVATAR = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B",
                        "#EF4444", "#06B6D4", "#EC4899", "#6366F1"]

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.es_admin = usuario is None or usuario.rol == "admin"
        self.c = colores_dashboard()
        self._miniaturas = {}

        self._construir_layout()
        self._cargar_asignaciones()
        self._cargar_devoluciones()
        if self.es_admin:
            self._cargar_mantenimientos()

    # ------------------------------------------------------------
    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        encabezado = ctk.CTkFrame(contenedor, fg_color="transparent")
        encabezado.pack(fill="x")

        crear_encabezado(
            encabezado, self.c,
            "Asignaciones activas",
            "Seguimiento de préstamos y devoluciones de equipo."
        ).pack(side="left")

        ctk.CTkButton(
            encabezado, text="+  Nuevo préstamo", width=170,
            command=self._on_nuevo_prestamo, **ESTILO_BOTON_PRIMARIO
        ).pack(side="right", anchor="e")

        # Enviar a mantenimiento es solo para admin (saca equipo de
        # circulación fuera del ciclo normal de préstamo/devolución).
        if self.es_admin:
            ctk.CTkButton(
                encabezado, text="Enviar a mantenimiento", width=190,
                command=self._on_enviar_mantenimiento, **ESTILO_BOTON_SECUNDARIO
            ).pack(side="right", anchor="e", padx=(0, 10))

        # Devolver escaneando: se escanea el artículo que regresa y se
        # abre directo su devolución (el lector termina con Enter).
        self.entrada_devolucion = ctk.CTkEntry(
            encabezado, width=260,
            placeholder_text="Escanear artículo para devolver...",
        )
        self.entrada_devolucion.pack(side="right", anchor="e", padx=(0, 10))
        self.entrada_devolucion.bind("<Return>", self._on_escaneo_devolucion)

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        # Buscador de préstamos activos (alumno, artículo, código o sección).
        self.entrada_buscar_activas = ctk.CTkEntry(
            interior, placeholder_text="Buscar por alumno, artículo, código o sección...",
        )
        self.entrada_buscar_activas.pack(fill="x", pady=(0, 10))
        self.entrada_buscar_activas.bind("<KeyRelease>", lambda _e: self._renderizar_asignaciones())

        crear_encabezado_tabla(
            interior, self.c,
            ["Alumno", "Artículo", "Sección", "Cant.", "Devolución esperada", "Estado", "Marca"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

        # Historial: quién ha devuelto cada equipo, y quién lo recibió.
        crear_encabezado(
            contenedor, self.c,
            "Devoluciones recientes",
            "Quiénes han devuelto equipo, quién registró la devolución y en qué condición llegó."
        ).pack(fill="x", pady=(20, 0))

        tarjeta_devueltos = crear_card(contenedor, self.c)
        tarjeta_devueltos.pack(fill="both", expand=True, pady=(12, 0))

        interior_devueltos = ctk.CTkFrame(tarjeta_devueltos, fg_color="transparent")
        interior_devueltos.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior_devueltos, self.c,
            ["Alumno", "Artículo", "Devuelto", "Registrado por", "Condición", "Marca"],
            self.ANCHOS_DEVUELTOS
        )

        self.lista_devueltos = ctk.CTkScrollableFrame(
            interior_devueltos, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
            height=180,
        )
        self.lista_devueltos.pack(fill="both", expand=True)

        # Equipos en mantenimiento: solo el admin los envía y los ve.
        if self.es_admin:
            crear_encabezado(
                contenedor, self.c,
                "Equipos en mantenimiento",
                "Artículos fuera de circulación por reparación/servicio."
            ).pack(fill="x", pady=(20, 0))

            tarjeta_mantenimiento = crear_card(contenedor, self.c)
            tarjeta_mantenimiento.pack(fill="both", expand=True, pady=(12, 0))

            interior_mantenimiento = ctk.CTkFrame(tarjeta_mantenimiento, fg_color="transparent")
            interior_mantenimiento.pack(fill="both", expand=True, padx=14, pady=14)

            crear_encabezado_tabla(
                interior_mantenimiento, self.c,
                ["Artículo", "Enviado a", "Causa", "Regreso estimado"],
                self.ANCHOS_MANTENIMIENTO
            )

            self.lista_mantenimiento = ctk.CTkScrollableFrame(
                interior_mantenimiento, fg_color="transparent",
                scrollbar_button_color=self.c["borde"],
                scrollbar_button_hover_color=COLORES["dash_hover_claro"],
                height=180,
            )
            self.lista_mantenimiento.pack(fill="both", expand=True)

    def _cargar_devoluciones(self):
        for hijo in self.lista_devueltos.winfo_children():
            hijo.destroy()

        historial = historial_alumnos()
        for d in listar_devoluciones():
            danado = bool(d.get("devuelto_danado"))
            if danado:
                fondo, texto_color, texto = COLORES["atrasado_fondo"], COLORES["atrasado_texto"], "Dañado"
            else:
                fondo, texto_color, texto = COLORES["disponible_fondo"], COLORES["disponible_texto"], "Bien"

            def _celda_condicion(celda, fondo=fondo, texto_color=texto_color, texto=texto):
                crear_badge(celda, texto, fondo, texto_color).place(relx=0, rely=0.5, anchor="w")

            acciones = None
            if danado:
                acciones = [(
                    "Daño",
                    lambda nombre=d["nombre_completo"], obs=d.get("observaciones_devolucion"),
                           foto=d.get("foto_devolucion"):
                        self._ver_dano(nombre, obs, foto)
                )]

            crear_fila_tabla(
                self.lista_devueltos, self.c,
                [
                    lambda celda, nombre=d["nombre_completo"]: self._celda_alumno(celda, nombre),
                    f"{d['articulo_nombre']} ({d['codigo_inventario']})",
                    d["hora_entrada_real"].strftime("%Y-%m-%d %H:%M"),
                    d["devuelto_por"] or "—",
                    _celda_condicion,
                    self._celda_marca(historial, d["nombre_completo"]),
                ],
                self.ANCHOS_DEVUELTOS,
                acciones=acciones,
            )

    def _cargar_mantenimientos(self):
        for hijo in self.lista_mantenimiento.winfo_children():
            hijo.destroy()

        activos = listar_en_mantenimiento()
        for m in activos:
            crear_fila_tabla(
                self.lista_mantenimiento, self.c,
                [
                    f"{m['articulo_nombre']} ({m['codigo_inventario']})",
                    m["destino"] or "—",
                    m["descripcion"] or "—",
                    m["fecha_retorno_estimada"].strftime("%Y-%m-%d") if m["fecha_retorno_estimada"] else "—",
                ],
                self.ANCHOS_MANTENIMIENTO,
                acciones=[
                    ("Regresó", lambda id_=m["id"]: self._on_marcar_regresado(id_)),
                ],
            )

        if not activos:
            ctk.CTkLabel(self.lista_mantenimiento, text="No hay equipos en mantenimiento.",
                         text_color=self.c["subtext"], font=("Segoe UI", 12)).pack(pady=20)

    def _on_marcar_regresado(self, mantenimiento_id):
        if not messagebox.askyesno("Confirmar", "¿Marcar este equipo como regresado de mantenimiento?"):
            return
        usuario_id = self.usuario.id if self.usuario else None
        try:
            marcar_regresado(mantenimiento_id, usuario_id)
        except ValueError as error:
            messagebox.showerror("Error", str(error))
            return
        self._cargar_mantenimientos()

    def _actualizar_kpis(self, asignaciones):
        for hijo in self.fila_kpis.winfo_children():
            hijo.destroy()

        total = len(asignaciones)
        vencidas = sum(1 for a in asignaciones if a.esta_vencida())

        datos = [
            (total,    "Activas",       COLORES["azul_primario"]),
            (vencidas, "Vencidas",      COLORES["atrasado_texto"]),
            (total - vencidas, "A tiempo", COLORES["disponible_texto"]),
        ]

        for numero, titulo, acento in datos:
            crear_kpi_card(self.fila_kpis, self.c, numero, titulo, acento).pack(
                side="left", expand=True, fill="both", padx=(0, 12)
            )

    def _celda_marca(self, historial, nombre):
        """Celda con el badge de la marca del alumno (No cuida / Tardista /
        ambas). Si todavía no tiene marca, muestra en gris cuánto lleva
        hacia cada límite (ej. "1/3 daños · 2/10 tarde"), o nada si no
        tiene incidencias."""
        datos = historial.get(clave_alumno(nombre), {})
        marca = datos.get("marca")
        if not marca:
            avance = []
            if datos.get("danos"):
                avance.append(f"{datos['danos']}/{DANOS_PARA_NO_CUIDA} daños")
            if datos.get("tardanzas"):
                avance.append(f"{datos['tardanzas']}/{TARDANZAS_PARA_TARDISTA} tarde")
            if not avance:
                return ""

            def _celda_avance(celda, texto=" · ".join(avance)):
                ctk.CTkLabel(celda, text=texto, font=("Segoe UI", 11), anchor="w",
                             text_color=self.c["subtext"]).place(relx=0, rely=0.5, anchor="w")
            return _celda_avance

        fondo, texto_color = (COLORES[k] for k in self.COLORES_MARCA[marca])

        def _celda(celda):
            crear_badge(celda, marca, fondo, texto_color).place(relx=0, rely=0.5, anchor="w")
        return _celda

    # ------------------------------------------------------------
    def _color_avatar(self, nombre):
        indice = sum(ord(c) for c in nombre) % len(self._COLORES_AVATAR)
        return self._COLORES_AVATAR[indice]

    def _iniciales(self, nombre):
        partes = nombre.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return partes[0][:2].upper()

    def _celda_alumno(self, celda, nombre):
        avatar = ctk.CTkLabel(celda, image=imagen_avatar(self._color_avatar(nombre), self._iniciales(nombre)),
                              text="",
                              width=30, height=30, fg_color="transparent")
        avatar.place(relx=0, rely=0.5, anchor="w")

        etiqueta = ctk.CTkLabel(celda, text=nombre, font=("Segoe UI", 12, "underline"), anchor="w",
                                text_color=self.c["texto"], cursor="hand2")
        etiqueta.place(x=40, rely=0.5, anchor="w")

        # Clic en el alumno (avatar o nombre): ver todo su historial.
        for widget in (avatar, etiqueta):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _e: self._ver_historial_alumno(nombre))

    def _ver_historial_alumno(self, nombre):
        prestamos = historial_prestamos_alumno(nombre)
        datos = historial_alumno(nombre)

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title(f"Historial — {nombre}")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=20, pady=20)

        fila_titulo = ctk.CTkFrame(interior, fg_color="transparent")
        fila_titulo.pack(fill="x")
        ctk.CTkLabel(fila_titulo, text=nombre, font=("Segoe UI", 16, "bold"),
                     text_color=self.c["texto"]).pack(side="left")
        marca_celda = self._celda_marca(self._historial_alumnos_o_cargar(), nombre)
        if callable(marca_celda):
            contenedor_marca = ctk.CTkFrame(fila_titulo, fg_color="transparent", width=200, height=30)
            contenedor_marca.pack(side="left", padx=(12, 0))
            marca_celda(contenedor_marca)

        activos = sum(1 for p in prestamos if p["hora_entrada_real"] is None)
        ctk.CTkLabel(
            interior, anchor="w", font=("Segoe UI", 12), text_color=self.c["subtext"],
            text=(f"{datos.get('seccion', '')} {datos.get('anio', '')}  ·  {datos.get('telefono') or '—'}  ·  "
                  f"{datos.get('correo') or '—'}\n"
                  f"{len(prestamos)} préstamo(s)  ·  {activos} activo(s)  ·  "
                  f"{datos['danos']} devuelto(s) dañado(s)  ·  {datos['tardanzas']} tardanza(s)"),
            justify="left",
        ).pack(fill="x", pady=(4, 12))

        anchos = (200, 45, 120, 120, 120, 90)
        crear_encabezado_tabla(interior, self.c,
                               ["Artículo", "Cant.", "Salida", "Esperada", "Devuelto", "Condición"], anchos)
        lista = ctk.CTkScrollableFrame(interior, fg_color="transparent", width=820, height=360,
                                       scrollbar_button_color=self.c["borde"])
        lista.pack(fill="both", expand=True)

        for p in prestamos:
            if p["hora_entrada_real"] is None:
                texto, fondo, color = (("Vencido", COLORES["atrasado_fondo"], COLORES["atrasado_texto"]) if p["tarde"]
                                       else ("Prestado", COLORES["en_uso_fondo"], COLORES["en_uso_texto"]))
            elif p["devuelto_danado"]:
                texto, fondo, color = "Dañado", COLORES["atrasado_fondo"], COLORES["atrasado_texto"]
            elif p["tarde"]:
                texto, fondo, color = "Tarde", COLORES["tardista_fondo"], COLORES["tardista_texto"]
            else:
                texto, fondo, color = "Bien", COLORES["disponible_fondo"], COLORES["disponible_texto"]

            def _celda_condicion(celda, texto=texto, fondo=fondo, color=color):
                crear_badge(celda, texto, fondo, color).place(relx=0, rely=0.5, anchor="w")

            acciones = None
            if p["devuelto_danado"]:
                acciones = [("Daño", lambda obs=p["observaciones_devolucion"], foto=p["foto_devolucion"]:
                             self._ver_dano(nombre, obs, foto))]

            crear_fila_tabla(
                lista, self.c,
                [
                    f"{p['articulo_nombre']} ({p['codigo_inventario']})",
                    str(p["cantidad"]),
                    p["hora_salida"].strftime("%Y-%m-%d %H:%M"),
                    p["hora_estimada_devolucion"].strftime("%Y-%m-%d %H:%M"),
                    p["hora_entrada_real"].strftime("%Y-%m-%d %H:%M") if p["hora_entrada_real"] else "—",
                    _celda_condicion,
                ],
                anchos,
                acciones=acciones,
            )

        if not prestamos:
            ctk.CTkLabel(lista, text="Sin préstamos registrados.", text_color=self.c["subtext"],
                         font=("Segoe UI", 12)).pack(pady=20)

        ctk.CTkButton(
            interior, text="Cerrar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x", pady=(12, 0))

    def _historial_alumnos_o_cargar(self):
        if not getattr(self, "_historial_alumnos", None):
            self._historial_alumnos = historial_alumnos()
        return self._historial_alumnos

    # ------------------------------------------------------------
    # Extender el plazo de un préstamo
    # ------------------------------------------------------------
    def _on_extender(self, asignacion_id):
        detalle = detalle_prestamo(asignacion_id)
        if not detalle:
            return

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Extender plazo")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(interior, anchor="w", font=("Segoe UI", 12, "bold"), text_color=self.c["texto"],
                     text=f"{detalle['nombre_completo']}  ·  {detalle['seccion']} {detalle['anio']}").pack(fill="x")
        ctk.CTkLabel(
            interior, anchor="w", font=("Segoe UI", 11),
            text_color=COLORES["atrasado_texto"] if detalle["vencido"] else self.c["subtext"],
            text=(f"{detalle['articulo_nombre']} ({detalle['codigo_inventario']})  ·  "
                  f"debía devolverse el {detalle['hora_estimada_devolucion']:%Y-%m-%d %H:%M}"
                  + ("  ·  VENCIDO" if detalle["vencido"] else "")),
        ).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(interior, text="Nueva fecha de devolución", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        # Por defecto: un día más que la fecha actual (o mañana si ya venció).
        base = max(detalle["hora_estimada_devolucion"].date(), date.today())
        sugerida = base + timedelta(days=1)
        calendario = Calendar(
            interior, selectmode="day", date_pattern="yyyy-mm-dd",
            year=sugerida.year, month=sugerida.month, day=sugerida.day,
            mindate=date.today(), showweeknumbers=False, font=("Segoe UI", 11),
            background=self.c["card_inner"], foreground=self.c["texto"],
            headersbackground=self.c["card_inner"], headersforeground=self.c["texto"],
            normalbackground=self.c["card"], normalforeground=self.c["texto"],
            weekendbackground=self.c["card"], weekendforeground=self.c["texto"],
            othermonthbackground=self.c["card_inner"], othermonthforeground=self.c["subtext"],
            selectbackground=COLORES["azul_primario"], selectforeground="#FFFFFF",
            bordercolor=self.c["borde"], borderwidth=1,
        )
        calendario.pack(fill="x", ipady=2)

        fila_hora = ctk.CTkFrame(interior, fg_color="transparent")
        fila_hora.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(fila_hora, text="Hora:", text_color=self.c["subtext"],
                     font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
        combo_hora = ctk.CTkComboBox(fila_hora, values=[f"{h:02d}" for h in range(24)],
                                     width=80, state="readonly")
        combo_hora.set(f"{detalle['hora_estimada_devolucion']:%H}")
        combo_hora.pack(side="left")
        ctk.CTkLabel(fila_hora, text=":", font=("Segoe UI", 16, "bold"),
                     text_color=self.c["texto"]).pack(side="left", padx=6)
        combo_minuto = ctk.CTkComboBox(fila_hora, values=["00", "15", "30", "45"],
                                       width=80, state="readonly")
        minuto = detalle["hora_estimada_devolucion"].minute
        combo_minuto.set(f"{minuto:02d}" if minuto in (0, 15, 30, 45) else "00")
        combo_minuto.pack(side="left")

        def _guardar_extension():
            nueva = f"{calendario.get_date()} {combo_hora.get()}:{combo_minuto.get()}"
            try:
                extender_prestamo(asignacion_id, nueva, self.usuario.id if self.usuario else None)
            except ValueError as error:
                messagebox.showerror("Error", str(error), parent=ventana)
                return
            ventana.destroy()
            self._cargar_asignaciones()

        ctk.CTkButton(interior, text="Guardar nuevo plazo", command=_guardar_extension,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(16, 0))
        ctk.CTkButton(
            interior, text="Cancelar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x", pady=(6, 0))
        ventana.bind("<Control-Return>", lambda _e: _guardar_extension())

    def _ver_foto_alumno(self, nombre, foto_path):
        if not foto_path or not os.path.isfile(foto_path):
            messagebox.showinfo("Foto del estudiante", f"{nombre} no tiene una foto registrada.")
            return

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title(f"Foto del estudiante — {nombre}")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(padx=20, pady=20)

        try:
            imagen = ctk.CTkImage(Image.open(foto_path), size=(320, 320))
        except Exception:
            messagebox.showerror("Error", "No se pudo abrir la foto del estudiante.")
            ventana.destroy()
            return

        etiqueta_imagen = ctk.CTkLabel(interior, image=imagen, text="")
        etiqueta_imagen.image = imagen
        etiqueta_imagen.pack(pady=(0, 14))

        ctk.CTkLabel(interior, text=nombre, font=("Segoe UI", 13, "bold"),
                     text_color=self.c["texto"]).pack(pady=(0, 14))

        ctk.CTkButton(
            interior, text="Cerrar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x")

    # ------------------------------------------------------------
    def _cargar_asignaciones(self):
        asignaciones = listar_asignaciones_activas()
        self._actualizar_kpis(asignaciones)

        # Vencidos primero; dentro de cada grupo, el que vence antes arriba.
        asignaciones.sort(key=lambda a: (not a.esta_vencida(), a.hora_estimada_devolucion))
        self._asignaciones = asignaciones
        self._articulos_por_id = {
            art.id: art for art in listar_articulos()
        }
        self._historial_alumnos = historial_alumnos()
        self._renderizar_asignaciones()

    def _renderizar_asignaciones(self):
        for hijo in self.lista.winfo_children():
            hijo.destroy()

        historial = self._historial_alumnos
        buscado = clave_alumno(self.entrada_buscar_activas.get())
        visibles = 0
        for a in self._asignaciones:
            articulo = self._articulos_por_id.get(a.articulo_id)
            texto_articulo = f"{articulo.nombre} ({articulo.codigo_inventario})" if articulo else "—"
            if buscado and buscado not in clave_alumno(
                f"{a.nombre_completo} {texto_articulo} {a.seccion} {a.anio}"
            ):
                continue
            visibles += 1
            vencida = a.esta_vencida()
            fondo, texto_color = (COLORES["atrasado_fondo"], COLORES["atrasado_texto"]) if vencida \
                else (COLORES["disponible_fondo"], COLORES["disponible_texto"])
            texto_estado = "Vencido" if vencida else "A tiempo"

            def _celda_estado(celda, fondo=fondo, texto_color=texto_color, texto_estado=texto_estado):
                crear_badge(celda, texto_estado, fondo, texto_color).place(relx=0, rely=0.5, anchor="w")

            crear_fila_tabla(
                self.lista, self.c,
                [
                    lambda celda, nombre=a.nombre_completo: self._celda_alumno(celda, nombre),
                    texto_articulo,
                    f"{a.seccion} {a.anio}",
                    str(a.cantidad),
                    a.hora_estimada_devolucion.strftime("%Y-%m-%d %H:%M"),
                    _celda_estado,
                    self._celda_marca(historial, a.nombre_completo),
                ],
                self.ANCHOS,
                acciones=[
                    ("Foto", lambda nombre=a.nombre_completo, foto=a.foto_alumno:
                        self._ver_foto_alumno(nombre, foto)),
                    ("Extender", lambda id_=a.id: self._on_extender(id_)),
                    ("Devolver", lambda id_=a.id: self._on_devolucion(id_)),
                ],
            )

        if not visibles:
            ctk.CTkLabel(
                self.lista, font=("Segoe UI", 12), text_color=self.c["subtext"],
                text="No hay préstamos que coincidan con la búsqueda." if buscado
                else "No hay préstamos activos.",
            ).pack(pady=20)

    def _ver_dano(self, nombre, observaciones, foto_path):
        descripcion = observaciones or "Sin descripción del daño."
        if not foto_path or not os.path.isfile(foto_path):
            messagebox.showinfo("Daño registrado", f"Equipo devuelto por {nombre}.\n\n{descripcion}")
            return

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title(f"Daño registrado — {nombre}")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(padx=20, pady=20)

        try:
            imagen = ctk.CTkImage(Image.open(foto_path), size=(320, 320))
        except Exception:
            messagebox.showerror("Error", "No se pudo abrir la foto del daño.")
            ventana.destroy()
            return

        etiqueta_imagen = ctk.CTkLabel(interior, image=imagen, text="")
        etiqueta_imagen.image = imagen
        etiqueta_imagen.pack(pady=(0, 14))

        ctk.CTkLabel(interior, text=f"Equipo devuelto por {nombre}", font=("Segoe UI", 13, "bold"),
                     text_color=self.c["texto"]).pack(pady=(0, 6))
        ctk.CTkLabel(interior, text=descripcion, font=("Segoe UI", 12), wraplength=320,
                     justify="left", text_color=self.c["subtext"]).pack(pady=(0, 14))

        ctk.CTkButton(
            interior, text="Cerrar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x")

    def _on_escaneo_devolucion(self, event=None):
        codigo = self.entrada_devolucion.get().strip()
        self.entrada_devolucion.delete(0, "end")
        if not codigo:
            return

        articulo = buscar_articulo_por_codigo(codigo)
        if articulo is None:
            messagebox.showwarning("Aviso", f"No se encontró ningún artículo con el código «{codigo}».")
            return

        prestamos = prestamos_activos_de_articulo(articulo.id)
        if not prestamos:
            messagebox.showinfo(
                "Sin préstamos",
                f"«{articulo.nombre}» ({articulo.codigo_inventario}) no tiene préstamos "
                "pendientes de devolución."
            )
        elif len(prestamos) == 1:
            self._on_devolucion(prestamos[0]["id"])
        else:
            self._elegir_prestamo_a_devolver(articulo, prestamos)

    def _elegir_prestamo_a_devolver(self, articulo, prestamos):
        """El artículo escaneado está prestado a varios alumnos (tiene
        stock): se elige de quién es la devolución."""
        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("¿Quién lo devuelve?")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(interior, text="¿Quién lo devuelve?", anchor="w",
                     font=("Segoe UI", 13, "bold"), text_color=self.c["texto"]).pack(fill="x")
        ctk.CTkLabel(
            interior, anchor="w", font=("Segoe UI", 11), text_color=self.c["subtext"],
            text=f"«{articulo.nombre}» ({articulo.codigo_inventario}) está prestado a "
                 f"{len(prestamos)} alumnos. Los vencidos aparecen primero.",
        ).pack(fill="x", pady=(2, 12))

        def _elegir(asignacion_id):
            ventana.destroy()
            self._on_devolucion(asignacion_id)

        for p in prestamos:
            texto = (f"{p['nombre_completo']}  ·  {p['seccion']} {p['anio']}  ·  "
                     f"{p['cantidad']} u.  ·  salió {p['hora_salida']:%Y-%m-%d}")
            if p["vencido"]:
                texto += "  ·  VENCIDO"
            ctk.CTkButton(
                interior, text=texto, anchor="w", height=34,
                fg_color=self.c["fila"], hover_color=self.c["card_inner"],
                text_color=COLORES["atrasado_texto"] if p["vencido"] else self.c["texto"],
                font=("Segoe UI", 12),
                command=lambda id_=p["id"]: _elegir(id_),
            ).pack(fill="x", pady=2)

        ctk.CTkButton(
            interior, text="Cancelar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x", pady=(10, 0))

    def _on_devolucion(self, asignacion_id):
        # Ventana de confirmación donde el profesor indica en qué
        # condición regresó el equipo; si llegó dañado puede describir
        # el daño y tomarle una foto (queda en la asignación, en el
        # historial y el artículo pasa a estado físico 'dañado').
        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Registrar devolución")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=20, pady=20)

        detalle = detalle_prestamo(asignacion_id)
        if detalle:
            ctk.CTkLabel(
                interior, anchor="w", justify="left", font=("Segoe UI", 12, "bold"),
                text_color=self.c["texto"],
                text=f"{detalle['nombre_completo']}  ·  {detalle['seccion']} {detalle['anio']}",
            ).pack(fill="x")
            ctk.CTkLabel(
                interior, anchor="w", justify="left", font=("Segoe UI", 11),
                text_color=COLORES["atrasado_texto"] if detalle["vencido"] else self.c["subtext"],
                text=f"{detalle['articulo_nombre']} ({detalle['codigo_inventario']})  ·  "
                     f"{detalle['cantidad']} unidad(es)"
                     + ("  ·  VENCIDO" if detalle["vencido"] else ""),
            ).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(interior, text="¿En qué condición regresó el equipo?", anchor="w",
                     font=("Segoe UI", 13, "bold"), text_color=self.c["texto"]).pack(fill="x", pady=(0, 10))

        # Devolución parcial: si se llevó varias unidades, puede devolver
        # solo algunas (el resto sigue prestado).
        entrada_cantidad_dev = None
        if detalle and detalle["cantidad"] > 1:
            fila_cantidad = ctk.CTkFrame(interior, fg_color="transparent")
            fila_cantidad.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(fila_cantidad, text="Unidades que devuelve:", text_color=self.c["texto"],
                         font=("Segoe UI", 12)).pack(side="left")
            entrada_cantidad_dev = ctk.CTkEntry(fila_cantidad, width=60)
            entrada_cantidad_dev.insert(0, str(detalle["cantidad"]))
            entrada_cantidad_dev.pack(side="left", padx=8)
            ctk.CTkLabel(fila_cantidad, text=f"de {detalle['cantidad']}", text_color=self.c["subtext"],
                         font=("Segoe UI", 12)).pack(side="left")

        condicion = ctk.StringVar(value="bien")

        ctk.CTkRadioButton(interior, text="En buen estado", variable=condicion, value="bien",
                           text_color=self.c["texto"]).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(interior, text="Regresó dañado", variable=condicion, value="danado",
                           text_color=self.c["texto"]).pack(anchor="w", pady=2)

        # Sección del daño: descripción + foto, siempre visible en la
        # misma ventana. Escribir una descripción o tomar una foto marca
        # automáticamente "Regresó dañado".
        frame_danos = ctk.CTkFrame(interior, fg_color="transparent")
        frame_danos.pack(fill="x")

        ctk.CTkLabel(frame_danos, text="Descripción del daño (opcional)", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(10, 2))
        caja_danos = ctk.CTkTextbox(frame_danos, height=90, width=360,
                                    fg_color=self.c["card_inner"], text_color=self.c["texto"])
        caja_danos.pack(fill="x")
        caja_danos.bind("<KeyRelease>", lambda _e: condicion.set("danado")
                        if caja_danos.get("1.0", "end").strip() else None)

        ctk.CTkLabel(frame_danos, text="Foto del daño (opcional)", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(10, 2))

        fila_foto = ctk.CTkFrame(frame_danos, fg_color="transparent")
        fila_foto.pack(fill="x")

        foto_estado = {"path": None}

        vista_previa_foto = ctk.CTkLabel(
            fila_foto, text="Sin foto", width=96, height=96, corner_radius=8,
            fg_color=self.c["card_inner"], text_color=self.c["subtext"],
            font=("Segoe UI", 10),
        )
        vista_previa_foto.pack(side="left")

        def _mostrar_previa_foto(ruta):
            if ruta and os.path.isfile(ruta):
                try:
                    imagen = ctk.CTkImage(Image.open(ruta), size=(96, 96))
                    vista_previa_foto.configure(image=imagen, text="")
                    vista_previa_foto.image = imagen
                    return
                except Exception:
                    pass
            vista_previa_foto.configure(image=None, text="Sin foto")
            vista_previa_foto.image = None

        def _abrir_camara():
            def _al_capturar(ruta):
                foto_estado["path"] = ruta
                _mostrar_previa_foto(ruta)
                condicion.set("danado")

            abrir_ventana_camara(
                ventana, self.c, "Tomar foto del daño",
                CARPETA_FOTOS_DEVOLUCIONES, _al_capturar, ESTILO_BOTON_PRIMARIO
            )

        botones_foto = ctk.CTkFrame(fila_foto, fg_color="transparent")
        botones_foto.pack(side="left", padx=(10, 0), fill="y")

        ctk.CTkButton(
            botones_foto, text="Tomar foto...", height=28,
            command=_abrir_camara, **ESTILO_BOTON_SECUNDARIO
        ).pack(anchor="w")

        ctk.CTkButton(
            botones_foto, text="Quitar foto", height=24, width=90,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
            command=lambda: (foto_estado.update(path=None), _mostrar_previa_foto(None))
        ).pack(anchor="w", pady=(4, 0))

        def _confirmar():
            danado = condicion.get() == "danado"
            observaciones = caja_danos.get("1.0", "end").strip() if danado else None
            foto = foto_estado["path"] if danado else None
            usuario_id = self.usuario.id if self.usuario else None
            cantidad_devuelta = None
            if entrada_cantidad_dev is not None:
                texto_cantidad = entrada_cantidad_dev.get().strip()
                if not texto_cantidad.isdigit():
                    messagebox.showerror("Error", "Escribe cuántas unidades devuelve.", parent=ventana)
                    return
                cantidad_devuelta = int(texto_cantidad)
            try:
                registrar_devolucion(asignacion_id, usuario_id, danado=danado,
                                     observaciones=observaciones, foto_devolucion=foto,
                                     cantidad_devuelta=cantidad_devuelta)
            except ValueError as error:
                messagebox.showerror("Error", str(error), parent=ventana)
                return
            ventana.destroy()
            self._cargar_asignaciones()
            self._cargar_devoluciones()
            self.entrada_devolucion.focus_set()  # listo para escanear el siguiente

        frame_botones = ctk.CTkFrame(interior, fg_color="transparent")
        frame_botones.pack(fill="x", pady=(16, 0))

        ctk.CTkButton(frame_botones, text="Registrar devolución", command=_confirmar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x")
        ventana.bind("<Control-Return>", lambda _e: _confirmar())
        ctk.CTkButton(
            frame_botones, text="Cancelar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------
    # FORMULARIO — nuevo préstamo
    # ------------------------------------------------------------
    def _on_nuevo_prestamo(self):
        # Solo artículos con unidades libres de verdad: uno puede estar
        # "disponible" en general pero con cantidad_disponible en 0 si ya
        # se prestó todo el stock.
        articulos_disponibles = [
            a for a in listar_articulos(estado_disponibilidad="disponible")
            if a.cantidad_disponible > 0
        ]
        profesores = listar_profesores()

        if not articulos_disponibles:
            messagebox.showwarning("Aviso", "No hay artículos disponibles para prestar.")
            return
        if not profesores:
            messagebox.showwarning("Aviso", "No hay profesores autorizados registrados.")
            return

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Nuevo préstamo")
        ventana.geometry("720x680")
        ventana.minsize(560, 560)
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        # Grid de 2 columnas iguales: cada campo vive en su propia celda
        # (label arriba, input abajo) en vez de apilarse uno debajo del
        # otro — así el modal queda compacto/cuadrado en vez de alargado.
        # minsize fuerza que cada columna sea ancha de verdad (no solo lo
        # que pida un combobox angosto), para que el modal quede más
        # ancho que alto en vez de angosto y estirado en altura.
        interior.grid_columnconfigure(0, weight=1, uniform="col", minsize=300)
        interior.grid_columnconfigure(1, weight=1, uniform="col", minsize=300)

        mapa_articulos = {
            f"{a.codigo_inventario} - {a.nombre} ({a.cantidad_disponible} disp.)": a.id
            for a in articulos_disponibles
        }
        mapa_profesores = {p["nombre_completo"]: p["id"] for p in profesores}

        campos = {}

        def _celda(fila, columna, colspan=1):
            frame = ctk.CTkFrame(interior, fg_color="transparent")
            frame.grid(row=fila, column=columna, columnspan=colspan, sticky="nsew", padx=6, pady=6)
            return frame

        def _campo_entry(fila, columna, etiqueta, valor_inicial="", colspan=1):
            frame = _celda(fila, columna, colspan)
            ctk.CTkLabel(frame, text=etiqueta, anchor="w", text_color=self.c["subtext"],
                         font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
            entrada = ctk.CTkEntry(frame)
            entrada.insert(0, valor_inicial)
            entrada.pack(fill="x")
            campos[etiqueta] = entrada
            return entrada

        def _campo_combo(fila, columna, etiqueta, valores, colspan=1):
            frame = _celda(fila, columna, colspan)
            ctk.CTkLabel(frame, text=etiqueta, anchor="w", text_color=self.c["subtext"],
                         font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
            combo = ctk.CTkComboBox(frame, values=valores, state="readonly")
            combo.pack(fill="x")
            return combo

        # Fila 0: Artículo (+ campo para escanear su código de barras) | Nombre del alumno
        frame_articulo = _celda(0, 0)
        ctk.CTkLabel(frame_articulo, text="Artículo", anchor="w", text_color=self.c["subtext"],
                     font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        combo_articulo = ctk.CTkComboBox(
            frame_articulo, values=list(mapa_articulos.keys()), state="readonly",
        )
        combo_articulo.pack(fill="x")

        # Un lector de código de barras USB escribe como si fuera un teclado
        # y termina con Enter: basta este campo enfocado (o escaneando
        # directo con la ventana abierta) para seleccionar el artículo sin
        # tener que buscarlo a mano en el combo.
        entrada_escaneo = ctk.CTkEntry(
            frame_articulo, placeholder_text="Escanear código de barras del artículo...",
        )
        entrada_escaneo.pack(fill="x", pady=(6, 0))

        # Cuántas unidades idénticas de este artículo se llevan (ej. 3
        # calculadoras iguales) en un solo préstamo, en vez de repetir el
        # formulario una vez por cada una. Vacío = 1.
        fila_cantidad = ctk.CTkFrame(frame_articulo, fg_color="transparent")
        fila_cantidad.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(fila_cantidad, text="Cantidad (vacío = 1):", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(side="left")
        entrada_cantidad = ctk.CTkEntry(fila_cantidad, width=60, placeholder_text="1")
        entrada_cantidad.pack(side="left", padx=(8, 0))

        def _on_escaneo_articulo(event=None):
            codigo = entrada_escaneo.get().strip()
            entrada_escaneo.delete(0, "end")
            if not codigo:
                return

            articulo = buscar_articulo_por_codigo(codigo)
            clave = next(
                (k for k, v in mapa_articulos.items() if articulo and v == articulo.id), None
            )
            if not clave:
                messagebox.showwarning(
                    "Aviso",
                    f"No se encontró un artículo disponible para prestar con el código «{codigo}»."
                )
                return

            combo_articulo.set(clave)

        entrada_escaneo.bind("<Return>", _on_escaneo_articulo)

        entrada_nombre = _campo_entry(0, 1, "Nombre completo del alumno")

        # Buscador de alumnos ya registrados: al escribir en el nombre se
        # despliega una lista de coincidencias (de préstamos anteriores);
        # al elegir una se llenan sección, año, teléfono y correo, y se
        # muestra su historial. Si no coincide nadie, se registra como
        # alumno nuevo con lo que se escriba a mano.
        historial_todos = historial_alumnos()
        TEXTO_AYUDA_NOMBRE = "Escribe para buscar entre los alumnos que ya han pedido préstamos."

        etiqueta_historial = ctk.CTkLabel(
            entrada_nombre.master, text=TEXTO_AYUDA_NOMBRE, anchor="w", justify="left",
            font=("Segoe UI", 10), text_color=self.c["subtext"], wraplength=300,
        )
        etiqueta_historial.pack(fill="x", pady=(4, 0))

        lista_sugerencias = ctk.CTkFrame(
            interior, fg_color=self.c["card_inner"], corner_radius=8,
            border_width=1, border_color=self.c["borde"],
        )
        sugerencias = []

        def _ocultar_sugerencias(_event=None):
            if lista_sugerencias.winfo_exists():  # la ventana pudo cerrarse ya
                lista_sugerencias.place_forget()

        def _texto_historial(datos):
            if datos["marca"]:
                return (f"⚠ Marcado como «{datos['marca']}» ({datos['danos']} daños, "
                        f"{datos['tardanzas']} tardanzas).", COLORES["atrasado_texto"])
            avance = []
            if datos["danos"]:
                avance.append(f"{datos['danos']}/{DANOS_PARA_NO_CUIDA} daños")
            if datos["tardanzas"]:
                avance.append(f"{datos['tardanzas']}/{TARDANZAS_PARA_TARDISTA} tarde")
            if avance:
                return f"Alumno registrado · {' · '.join(avance)}", COLORES["danado_texto"]
            return "Alumno registrado · sin incidencias", COLORES["disponible_texto"]

        def _elegir_alumno(datos):
            for etiqueta, valor in (
                ("Nombre completo del alumno", datos["nombre"]),
                ("Sección", datos["seccion"]),
                ("Año", datos["anio"]),
                ("Teléfono", datos["telefono"]),
                ("Correo", datos["correo"]),
            ):
                campos[etiqueta].delete(0, "end")
                campos[etiqueta].insert(0, valor or "")
            texto, color = _texto_historial(datos)
            etiqueta_historial.configure(text=texto, text_color=color)
            _ocultar_sugerencias()

        def _actualizar_sugerencias(event=None):
            if event is not None and event.keysym in ("Return", "KP_Enter", "Escape", "Tab"):
                return
            for hijo in lista_sugerencias.winfo_children():
                hijo.destroy()

            texto = entrada_nombre.get()
            sugerencias[:] = buscar_alumnos(texto, historial=historial_todos)

            if not texto.strip():
                etiqueta_historial.configure(text=TEXTO_AYUDA_NOMBRE, text_color=self.c["subtext"])
            elif not sugerencias:
                etiqueta_historial.configure(text="No está registrado: se guardará como alumno nuevo.",
                                             text_color=self.c["subtext"])
            else:
                etiqueta_historial.configure(text="Elige un alumno de la lista (o Enter para el primero).",
                                             text_color=self.c["subtext"])

            if not sugerencias:
                _ocultar_sugerencias()
                return

            for datos in sugerencias:
                texto_opcion = f"{datos['nombre']}   ·   {datos['seccion']} {datos['anio']}"
                if datos["marca"]:
                    texto_opcion += f"   ⚠ {datos['marca']}"
                ctk.CTkButton(
                    lista_sugerencias, text=texto_opcion, anchor="w", height=30,
                    fg_color="transparent", hover_color=self.c["fila"],
                    text_color=COLORES["atrasado_texto"] if datos["marca"] else self.c["texto"],
                    font=("Segoe UI", 12),
                    command=lambda d=datos: _elegir_alumno(d),
                ).pack(fill="x", padx=4, pady=1)

            lista_sugerencias.place(in_=entrada_nombre, x=0, rely=1.0, y=2, relwidth=1.0)
            lista_sugerencias.lift()

        def _on_enter_nombre(_event=None):
            if sugerencias and lista_sugerencias.winfo_ismapped():
                _elegir_alumno(sugerencias[0])

        entrada_nombre.bind("<KeyRelease>", _actualizar_sugerencias)
        entrada_nombre.bind("<Return>", _on_enter_nombre)
        def _on_escape_nombre(_event=None):
            # Si la lista de sugerencias está abierta, Esc solo la cierra
            # (sin cerrar todo el formulario).
            if lista_sugerencias.winfo_ismapped():
                _ocultar_sugerencias()
                return "break"
            return None

        entrada_nombre.bind("<Escape>", _on_escape_nombre)
        # Con retraso, para que el clic en una opción de la lista alcance
        # a registrarse antes de ocultarla.
        entrada_nombre.bind("<FocusOut>", lambda _e: ventana.after(250, _ocultar_sugerencias))

        # Fila 1: Sección | Año
        _campo_entry(1, 0, "Sección")
        _campo_entry(1, 1, "Año")

        # Fila 2: Teléfono | Correo
        _campo_entry(2, 0, "Teléfono")
        _campo_entry(2, 1, "Correo")

        # Fila 3: Profesor que autoriza (ancho completo)
        combo_profesor = _campo_combo(3, 0, "Profesor que autoriza", list(mapa_profesores.keys()), colspan=2)

        # Preseleccionar el último profesor usado (si sigue activo).
        try:
            ultimo_profesor = int(leer_ajuste("ultimo_profesor_id") or 0)
        except (ValueError, Exception):  # noqa: BLE001 - sin ajuste o sin conexión: no preseleccionar
            ultimo_profesor = 0
        for nombre_profesor, id_profesor in mapa_profesores.items():
            if id_profesor == ultimo_profesor:
                combo_profesor.set(nombre_profesor)

        # Fila 4: foto del alumno (ancho completo) — evidencia de quién
        # se lleva el equipo, tomada con la cámara al momento del préstamo.
        frame_foto = _celda(4, 0, colspan=2)
        ctk.CTkLabel(frame_foto, text="Foto del alumno (opcional)", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        fila_foto = ctk.CTkFrame(frame_foto, fg_color="transparent")
        fila_foto.pack(fill="x")

        foto_estado = {"path": None}

        vista_previa_foto = ctk.CTkLabel(
            fila_foto, text="Sin foto", width=96, height=96, corner_radius=8,
            fg_color=self.c["card_inner"], text_color=self.c["subtext"],
            font=("Segoe UI", 10),
        )
        vista_previa_foto.pack(side="left")

        def _mostrar_previa_foto(ruta):
            if ruta and os.path.isfile(ruta):
                try:
                    imagen = ctk.CTkImage(Image.open(ruta), size=(96, 96))
                    vista_previa_foto.configure(image=imagen, text="")
                    vista_previa_foto.image = imagen
                    return
                except Exception:
                    pass
            vista_previa_foto.configure(image=None, text="Sin foto")
            vista_previa_foto.image = None

        def _abrir_camara():
            def _al_capturar(ruta):
                foto_estado["path"] = ruta
                _mostrar_previa_foto(ruta)

            abrir_ventana_camara(
                ventana, self.c, "Tomar foto del alumno",
                CARPETA_FOTOS_ALUMNOS, _al_capturar, ESTILO_BOTON_PRIMARIO
            )

        botones_foto = ctk.CTkFrame(fila_foto, fg_color="transparent")
        botones_foto.pack(side="left", padx=(10, 0), fill="y")

        ctk.CTkButton(
            botones_foto, text="Tomar foto...", height=28,
            command=_abrir_camara, **ESTILO_BOTON_SECUNDARIO
        ).pack(anchor="w")

        ctk.CTkButton(
            botones_foto, text="Quitar foto", height=24, width=90,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
            command=lambda: (foto_estado.update(path=None), _mostrar_previa_foto(None))
        ).pack(anchor="w", pady=(4, 0))

        # Fila 5: calendario y hora, uno al lado del otro (ahorra una fila
        # completa de alto frente a apilarlos, y mantiene el modal ancho).
        frame_calendario = _celda(5, 0)
        ctk.CTkLabel(frame_calendario, text="Fecha de devolución esperada", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        mañana = date.today() + timedelta(days=1)
        calendario = Calendar(
            frame_calendario,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            year=mañana.year, month=mañana.month, day=mañana.day,
            mindate=date.today(),
            showweeknumbers=False,
            font=("Segoe UI", 11),
            background=self.c["card_inner"],
            foreground=self.c["texto"],
            headersbackground=self.c["card_inner"],
            headersforeground=self.c["texto"],
            normalbackground=self.c["card"],
            normalforeground=self.c["texto"],
            weekendbackground=self.c["card"],
            weekendforeground=self.c["texto"],
            othermonthbackground=self.c["card_inner"],
            othermonthforeground=self.c["subtext"],
            selectbackground=COLORES["azul_primario"],
            selectforeground="#FFFFFF",
            bordercolor=self.c["borde"],
            borderwidth=1,
        )
        calendario.pack(fill="x", ipady=2)

        # Hora de devolución: junto al calendario, misma fila
        frame_hora = _celda(5, 1)
        ctk.CTkLabel(frame_hora, text="Hora de devolución esperada", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        fila_hora = ctk.CTkFrame(frame_hora, fg_color="transparent")
        fila_hora.pack(fill="x")

        combo_hora = ctk.CTkComboBox(
            fila_hora, values=[f"{h:02d}" for h in range(24)], width=90, state="readonly"
        )
        combo_hora.set("17")
        combo_hora.pack(side="left")

        ctk.CTkLabel(
            fila_hora, text=":", font=("Segoe UI", 16, "bold"), text_color=self.c["texto"]
        ).pack(side="left", padx=8)

        combo_minuto = ctk.CTkComboBox(
            fila_hora, values=["00", "15", "30", "45"], width=90, state="readonly"
        )
        combo_minuto.set("00")
        combo_minuto.pack(side="left")

        def _guardar():
            nombre = campos["Nombre completo del alumno"].get().strip()
            seccion = campos["Sección"].get().strip()
            anio = campos["Año"].get().strip()
            telefono = campos["Teléfono"].get().strip()
            correo = campos["Correo"].get().strip()
            hora_dev = f"{calendario.get_date()} {combo_hora.get()}:{combo_minuto.get()}"

            if not all([nombre, seccion, anio, telefono, correo, combo_articulo.get(), combo_profesor.get()]):
                messagebox.showerror("Error", "Todos los campos son obligatorios.")
                return
            if not correo_valido(correo):
                messagebox.showerror("Error", "Correo inválido.")
                return

            cantidad_texto = entrada_cantidad.get().strip()
            cantidad = 1
            if cantidad_texto:
                if not cantidad_texto.isdigit() or int(cantidad_texto) < 1:
                    messagebox.showerror("Error", "La cantidad debe ser un número entero de 1 o más.")
                    return
                cantidad = int(cantidad_texto)

            articulo_id_elegido = mapa_articulos[combo_articulo.get()]

            historial = historial_alumno(nombre)
            if historial["marca"]:
                motivos = []
                if historial["danos"] >= DANOS_PARA_NO_CUIDA:
                    motivos.append(f"• Ha devuelto equipo dañado {historial['danos']} veces.")
                if historial["tardanzas"] >= TARDANZAS_PARA_TARDISTA:
                    motivos.append(f"• Ha devuelto tarde {historial['tardanzas']} veces.")
                if not messagebox.askyesno(
                    "Alumno marcado",
                    f"{nombre} está marcado como «{historial['marca']}».\n\n"
                    + "\n".join(motivos)
                    + "\n\n¿Registrar el préstamo de todas formas?",
                    icon="warning", parent=ventana,
                ):
                    return

            # Una sola fila de asignación con `cantidad` unidades del mismo
            # artículo: el controlador valida y descuenta el stock en una
            # sola operación (antes esto hacía un préstamo por unidad, lo
            # que volvía lenta la pantalla al pedir cantidades grandes).
            try:
                registrar_prestamo(
                    articulo_id=articulo_id_elegido,
                    nombre_completo=nombre,
                    seccion=seccion,
                    anio=anio,
                    telefono=telefono,
                    correo=correo,
                    profesor_autoriza_id=mapa_profesores[combo_profesor.get()],
                    hora_estimada_devolucion=hora_dev,
                    usuario_registro_id=self.usuario.id if self.usuario else None,
                    foto_alumno=foto_estado["path"],
                    cantidad=cantidad,
                )
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return

            try:
                guardar_ajuste("ultimo_profesor_id", str(mapa_profesores[combo_profesor.get()]))
            except Exception:  # noqa: BLE001 - recordar el profesor es solo una comodidad
                pass

            ventana.destroy()
            self._cargar_asignaciones()

        # Fila 6: botón de guardar (ancho completo)
        frame_boton = _celda(6, 0, colspan=2)
        ctk.CTkButton(frame_boton, text="Registrar préstamo", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(6, 0))
        ventana.bind("<Control-Return>", lambda _e: _guardar())

        # Ajusta la ventana al tamaño real que pide el contenido (evita
        # que el calendario u otro campo queden cortados sin scroll) y
        # respeta un ancho mínimo para que el modal quede cuadrado/ancho.
        ventana.update_idletasks()
        alto = tarjeta.winfo_reqheight() + 32
        ancho = max(760, tarjeta.winfo_reqwidth() + 32, alto + 40)
        ventana.geometry(f"{ancho}x{alto}")

    # ------------------------------------------------------------
    # FORMULARIO — enviar a mantenimiento (solo admin)
    # ------------------------------------------------------------
    def _on_enviar_mantenimiento(self):
        articulos_disponibles = [
            a for a in listar_articulos(estado_disponibilidad="disponible")
            if a.cantidad_disponible > 0
        ]
        if not articulos_disponibles:
            messagebox.showwarning("Aviso", "No hay artículos disponibles para enviar a mantenimiento.")
            return

        ventana = ctk.CTkToplevel(self)
        centrar_ventana(ventana)
        ventana.title("Enviar a mantenimiento")
        ventana.geometry("720x620")
        ventana.minsize(560, 520)
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        interior.grid_columnconfigure(0, weight=1, uniform="col", minsize=300)
        interior.grid_columnconfigure(1, weight=1, uniform="col", minsize=300)

        mapa_articulos = {
            f"{a.codigo_inventario} - {a.nombre} ({a.cantidad_disponible} disp.)": a.id
            for a in articulos_disponibles
        }

        campos = {}

        def _celda(fila, columna, colspan=1):
            frame = ctk.CTkFrame(interior, fg_color="transparent")
            frame.grid(row=fila, column=columna, columnspan=colspan, sticky="nsew", padx=6, pady=6)
            return frame

        def _campo_entry(fila, columna, etiqueta, valor_inicial="", colspan=1):
            frame = _celda(fila, columna, colspan)
            ctk.CTkLabel(frame, text=etiqueta, anchor="w", text_color=self.c["subtext"],
                         font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
            entrada = ctk.CTkEntry(frame)
            entrada.insert(0, valor_inicial)
            entrada.pack(fill="x")
            campos[etiqueta] = entrada
            return entrada

        # Fila 0: Artículo (+ escaneo de código de barras)
        frame_articulo = _celda(0, 0, colspan=2)
        ctk.CTkLabel(frame_articulo, text="Equipo", anchor="w", text_color=self.c["subtext"],
                     font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        combo_articulo = ctk.CTkComboBox(
            frame_articulo, values=list(mapa_articulos.keys()), state="readonly",
        )
        combo_articulo.pack(fill="x")

        entrada_escaneo = ctk.CTkEntry(
            frame_articulo, placeholder_text="Escanear código de barras del artículo...",
        )
        entrada_escaneo.pack(fill="x", pady=(6, 0))

        def _on_escaneo_articulo(event=None):
            codigo = entrada_escaneo.get().strip()
            entrada_escaneo.delete(0, "end")
            if not codigo:
                return
            articulo = buscar_articulo_por_codigo(codigo)
            clave = next(
                (k for k, v in mapa_articulos.items() if articulo and v == articulo.id), None
            )
            if not clave:
                messagebox.showwarning(
                    "Aviso",
                    f"No se encontró un artículo disponible con el código «{codigo}»."
                )
                return
            combo_articulo.set(clave)

        entrada_escaneo.bind("<Return>", _on_escaneo_articulo)

        # Fila 1: Enviado a (destino) | Técnico encargado (opcional)
        _campo_entry(1, 0, "Enviado a (taller, proveedor...)")
        _campo_entry(1, 1, "Técnico encargado (opcional)")

        # Fila 2: Causa (ancho completo)
        _campo_entry(2, 0, "Causa del mantenimiento", colspan=2)

        # Fila 3: Costo estimado (opcional)
        _campo_entry(3, 0, "Costo estimado (opcional)")

        # Fila 4: Fecha de envío | Fecha estipulada de devolución
        frame_fecha_envio = _celda(4, 0)
        ctk.CTkLabel(frame_fecha_envio, text="Fecha de envío", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
        calendario_envio = Calendar(
            frame_fecha_envio, selectmode="day", date_pattern="yyyy-mm-dd",
            maxdate=date.today(), showweeknumbers=False, font=("Segoe UI", 11),
            background=self.c["card_inner"], foreground=self.c["texto"],
            headersbackground=self.c["card_inner"], headersforeground=self.c["texto"],
            normalbackground=self.c["card"], normalforeground=self.c["texto"],
            weekendbackground=self.c["card"], weekendforeground=self.c["texto"],
            othermonthbackground=self.c["card_inner"], othermonthforeground=self.c["subtext"],
            selectbackground=COLORES["azul_primario"], selectforeground="#FFFFFF",
            bordercolor=self.c["borde"], borderwidth=1,
        )
        calendario_envio.pack(fill="x", ipady=2)

        frame_fecha_regreso = _celda(4, 1)
        ctk.CTkLabel(frame_fecha_regreso, text="Regreso estipulado", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
        mañana = date.today() + timedelta(days=1)
        calendario_regreso = Calendar(
            frame_fecha_regreso, selectmode="day", date_pattern="yyyy-mm-dd",
            year=mañana.year, month=mañana.month, day=mañana.day,
            mindate=date.today(), showweeknumbers=False, font=("Segoe UI", 11),
            background=self.c["card_inner"], foreground=self.c["texto"],
            headersbackground=self.c["card_inner"], headersforeground=self.c["texto"],
            normalbackground=self.c["card"], normalforeground=self.c["texto"],
            weekendbackground=self.c["card"], weekendforeground=self.c["texto"],
            othermonthbackground=self.c["card_inner"], othermonthforeground=self.c["subtext"],
            selectbackground=COLORES["azul_primario"], selectforeground="#FFFFFF",
            bordercolor=self.c["borde"], borderwidth=1,
        )
        calendario_regreso.pack(fill="x", ipady=2)

        def _guardar_mantenimiento():
            if not combo_articulo.get():
                messagebox.showerror("Error", "Selecciona (o escanea) el equipo a enviar.")
                return
            destino = campos["Enviado a (taller, proveedor...)"].get().strip()
            causa = campos["Causa del mantenimiento"].get().strip()
            if not destino or not causa:
                messagebox.showerror("Error", "«Enviado a» y «Causa» son obligatorios.")
                return

            costo_texto = campos["Costo estimado (opcional)"].get().strip()
            costo = None
            if costo_texto:
                try:
                    costo = float(costo_texto.replace(",", ""))
                except ValueError:
                    messagebox.showerror("Error", "El costo estimado debe ser un número.")
                    return

            try:
                enviar_a_mantenimiento(
                    articulo_id=mapa_articulos[combo_articulo.get()],
                    fecha=calendario_envio.get_date(),
                    destino=destino,
                    causa=causa,
                    fecha_retorno_estimada=calendario_regreso.get_date(),
                    tecnico=campos["Técnico encargado (opcional)"].get().strip() or None,
                    costo=costo,
                    usuario_id=self.usuario.id if self.usuario else None,
                )
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return

            ventana.destroy()
            self._cargar_mantenimientos()

        frame_boton = _celda(5, 0, colspan=2)
        ctk.CTkButton(frame_boton, text="Enviar a mantenimiento", command=_guardar_mantenimiento,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(6, 0))
        ventana.bind("<Control-Return>", lambda _e: _guardar_mantenimiento())

        ventana.update_idletasks()
        alto = tarjeta.winfo_reqheight() + 32
        ancho = max(760, tarjeta.winfo_reqwidth() + 32, alto + 40)
        ventana.geometry(f"{ancho}x{alto}")
