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
    listar_devoluciones
)
from controllers.inventario_controller import listar_articulos, buscar_articulo_por_codigo
from controllers.auth_controller import listar_profesores
from utils.validaciones import correo_valido
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card,
    crear_encabezado_tabla, crear_fila_tabla, crear_badge,
    abrir_ventana_camara
)

CARPETA_FOTOS_ALUMNOS = os.path.join("assets", "fotos_prestamos")


class AsignacionView(ctk.CTkFrame):

    ANCHOS = (160, 70, 60, 130, 130, 90)
    ANCHOS_DEVUELTOS = (170, 180, 140, 140)
    _COLORES_AVATAR = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B",
                        "#EF4444", "#06B6D4", "#EC4899", "#6366F1"]

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.c = colores_dashboard()
        self._miniaturas = {}

        self._construir_layout()
        self._cargar_asignaciones()
        self._cargar_devoluciones()

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

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior, self.c,
            ["Alumno", "Sección", "Cant.", "Salida", "Devolución esperada", "Estado"],
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
            "Quiénes han devuelto equipo y quién registró la devolución."
        ).pack(fill="x", pady=(20, 0))

        tarjeta_devueltos = crear_card(contenedor, self.c)
        tarjeta_devueltos.pack(fill="both", expand=True, pady=(12, 0))

        interior_devueltos = ctk.CTkFrame(tarjeta_devueltos, fg_color="transparent")
        interior_devueltos.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior_devueltos, self.c,
            ["Alumno", "Artículo", "Devuelto", "Registrado por"],
            self.ANCHOS_DEVUELTOS
        )

        self.lista_devueltos = ctk.CTkScrollableFrame(
            interior_devueltos, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
            height=180,
        )
        self.lista_devueltos.pack(fill="both", expand=True)

    def _cargar_devoluciones(self):
        for hijo in self.lista_devueltos.winfo_children():
            hijo.destroy()

        for d in listar_devoluciones():
            crear_fila_tabla(
                self.lista_devueltos, self.c,
                [
                    lambda celda, nombre=d["nombre_completo"]: self._celda_alumno(celda, nombre),
                    f"{d['articulo_nombre']} ({d['codigo_inventario']})",
                    d["hora_entrada_real"].strftime("%Y-%m-%d %H:%M"),
                    d["devuelto_por"] or "—",
                ],
                self.ANCHOS_DEVUELTOS,
            )

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
        color_av = self._color_avatar(nombre)

        avatar = ctk.CTkFrame(celda, width=30, height=30, fg_color=color_av, corner_radius=15)
        avatar.place(relx=0, rely=0.5, anchor="w")
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=self._iniciales(nombre), font=("Segoe UI", 11, "bold"),
                     text_color="#FFFFFF").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(celda, text=nombre, font=("Segoe UI", 12), anchor="w",
                     text_color=self.c["texto"]).place(x=40, rely=0.5, anchor="w")

    def _ver_foto_alumno(self, nombre, foto_path):
        if not foto_path or not os.path.isfile(foto_path):
            messagebox.showinfo("Foto del estudiante", f"{nombre} no tiene una foto registrada.")
            return

        ventana = ctk.CTkToplevel(self)
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

        for hijo in self.lista.winfo_children():
            hijo.destroy()

        for a in asignaciones:
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
                    f"{a.seccion} {a.anio}",
                    str(a.cantidad),
                    a.hora_salida.strftime("%Y-%m-%d %H:%M"),
                    a.hora_estimada_devolucion.strftime("%Y-%m-%d %H:%M"),
                    _celda_estado,
                ],
                self.ANCHOS,
                acciones=[
                    ("Foto", lambda nombre=a.nombre_completo, foto=a.foto_alumno:
                        self._ver_foto_alumno(nombre, foto)),
                    ("Devolver", lambda id_=a.id: self._on_devolucion(id_)),
                ],
            )

    def _on_devolucion(self, asignacion_id):
        if not messagebox.askyesno("Confirmar", "¿Registrar la devolución de este equipo?"):
            return
        usuario_id = self.usuario.id if self.usuario else None
        registrar_devolucion(asignacion_id, usuario_id)
        self._cargar_asignaciones()
        self._cargar_devoluciones()

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

        _campo_entry(0, 1, "Nombre completo del alumno")

        # Fila 1: Sección | Año
        _campo_entry(1, 0, "Sección")
        _campo_entry(1, 1, "Año")

        # Fila 2: Teléfono | Correo
        _campo_entry(2, 0, "Teléfono")
        _campo_entry(2, 1, "Correo")

        # Fila 3: Profesor que autoriza (ancho completo)
        combo_profesor = _campo_combo(3, 0, "Profesor que autoriza", list(mapa_profesores.keys()), colspan=2)

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

            ventana.destroy()
            self._cargar_asignaciones()

        # Fila 6: botón de guardar (ancho completo)
        frame_boton = _celda(6, 0, colspan=2)
        ctk.CTkButton(frame_boton, text="Registrar préstamo", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(6, 0))

        # Ajusta la ventana al tamaño real que pide el contenido (evita
        # que el calendario u otro campo queden cortados sin scroll) y
        # respeta un ancho mínimo para que el modal quede cuadrado/ancho.
        ventana.update_idletasks()
        alto = tarjeta.winfo_reqheight() + 32
        ancho = max(760, tarjeta.winfo_reqwidth() + 32, alto + 40)
        ventana.geometry(f"{ancho}x{alto}")
