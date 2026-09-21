"""
views/inventario_view.py — Pantalla de inventario.

Frame embebido dentro del área de contenido del Dashboard (se muestra
al navegar desde el sidebar, reemplazando la vista anterior): arma su
layout con los colores de views/tema.py y los componentes compartidos
de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import os
import shutil
import uuid
from datetime import date

import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkcalendar import Calendar
from PIL import Image

from controllers.inventario_controller import (
    listar_articulos, agregar_articulo, editar_articulo, dar_de_baja, eliminar_articulo,
    listar_categorias, agregar_categoria, editar_categoria, eliminar_categoria,
    generar_etiqueta, buscar_articulo_por_codigo
)
from utils.validaciones import campo_no_vacio
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, ESTILO_BOTON_SECUNDARIO, color_badge
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card,
    crear_encabezado_tabla, crear_fila_tabla, crear_badge,
    abrir_ventana_camara
)

CARPETA_FOTOS = os.path.join("assets", "fotos_articulos")
EXTENSIONES_FOTO = (".png", ".jpg", ".jpeg", ".gif", ".webp")


class InventarioView(ctk.CTkFrame):

    ANCHOS = (50, 80, 150, 100, 90, 70, 100)
    TAMANO_PAGINA = 10

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.c = colores_dashboard()
        self._miniaturas = {}
        self._articulos_filtrados = []
        self._pagina_actual = 0
        self._refrescar_categorias()

        self._construir_layout()
        self._cargar_articulos()

    def _refrescar_categorias(self):
        self._categorias = {cat["nombre"]: cat["id"] for cat in listar_categorias()}

    # ------------------------------------------------------------
    def _construir_layout(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        encabezado = ctk.CTkFrame(contenedor, fg_color="transparent")
        encabezado.pack(fill="x")

        crear_encabezado(
            encabezado, self.c,
            "Inventario de equipos",
            "Control del ciclo de vida de todo el equipo tecnológico y ofimático."
        ).pack(side="left")

        ctk.CTkButton(
            encabezado, text="+  Nuevo artículo", width=160,
            command=self._on_agregar, **ESTILO_BOTON_PRIMARIO
        ).pack(side="right", anchor="e")

        ctk.CTkButton(
            encabezado, text="Categorías", width=120,
            command=self._abrir_categorias, **ESTILO_BOTON_SECUNDARIO
        ).pack(side="right", anchor="e", padx=(0, 10))

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        # Barra de búsqueda / escaneo: un lector de código de barras USB
        # actúa como teclado (escribe el código y termina con Enter), así
        # que basta un CTkEntry enfocado — sin hardware ni driver especial.
        fila_busqueda = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_busqueda.pack(fill="x", pady=(0, 12))

        self.entrada_busqueda = ctk.CTkEntry(
            fila_busqueda,
            placeholder_text="Buscar por nombre o código... (o escanear un código de barras)",
        )
        self.entrada_busqueda.pack(side="left", fill="x", expand=True)
        self.entrada_busqueda.bind("<Return>", self._on_escaneo)
        self.entrada_busqueda.bind("<KeyRelease>", self._on_busqueda_cambio)

        ctk.CTkButton(
            fila_busqueda, text="Limpiar", width=90,
            command=self._on_limpiar_busqueda, **ESTILO_BOTON_SECUNDARIO
        ).pack(side="left", padx=(10, 0))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior, self.c,
            ["Foto", "Código", "Nombre", "Categoría", "Estado", "Stock", "Ubicación"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

        # Paginación: en vez de renderizar cientos de filas a la vez (lo
        # que laggeaba la vista), se muestran de a TAMANO_PAGINA y se
        # avanza/retrocede entre bloques, como el listado de productos de
        # una tienda en línea.
        fila_paginacion = ctk.CTkFrame(interior, fg_color="transparent")
        fila_paginacion.pack(fill="x", pady=(10, 0))

        self.boton_pagina_anterior = ctk.CTkButton(
            fila_paginacion, text="< Anterior", width=110,
            command=self._pagina_anterior, **ESTILO_BOTON_SECUNDARIO
        )
        self.boton_pagina_anterior.pack(side="left")

        self.etiqueta_paginacion = ctk.CTkLabel(
            fila_paginacion, text="", text_color=self.c["subtext"], font=("Segoe UI", 12)
        )
        self.etiqueta_paginacion.pack(side="left", expand=True)

        self.boton_pagina_siguiente = ctk.CTkButton(
            fila_paginacion, text="Siguiente >", width=110,
            command=self._pagina_siguiente, **ESTILO_BOTON_SECUNDARIO
        )
        self.boton_pagina_siguiente.pack(side="right")

    def _actualizar_kpis(self, articulos):
        for hijo in self.fila_kpis.winfo_children():
            hijo.destroy()

        # Cada fila es un tipo de artículo con cantidad_total/
        # cantidad_disponible, así que los KPIs suman unidades en stock
        # en vez de contar filas.
        activos = [a for a in articulos if a.estado_disponibilidad == "disponible"]
        disponibles = sum(a.cantidad_disponible for a in activos)
        prestados = sum(a.cantidad_total - a.cantidad_disponible for a in activos)
        de_baja = sum(a.cantidad_total for a in articulos if a.estado_disponibilidad == "de_baja")
        total = disponibles + prestados + de_baja

        datos = [
            (total,       "Total de equipos", COLORES["azul_primario"]),
            (disponibles, "Disponibles",       COLORES["disponible_texto"]),
            (prestados,   "Prestados",         COLORES["danado_texto"]),
            (de_baja,     "De baja",           COLORES["de_baja_texto"]),
        ]

        for numero, titulo, acento in datos:
            crear_kpi_card(self.fila_kpis, self.c, numero, titulo, acento).pack(
                side="left", expand=True, fill="both", padx=(0, 12)
            )

    # ------------------------------------------------------------
    def _miniatura(self, ruta):
        """Devuelve un CTkImage en caché (36x36) para la foto del artículo,
        o None si no tiene foto o el archivo ya no existe."""
        if not ruta or not os.path.isfile(ruta):
            return None
        if ruta not in self._miniaturas:
            try:
                self._miniaturas[ruta] = ctk.CTkImage(Image.open(ruta), size=(36, 36))
            except Exception:
                self._miniaturas[ruta] = None
        return self._miniaturas[ruta]

    def _cargar_articulos(self, filtro_texto=None):
        articulos = listar_articulos()

        if filtro_texto:
            filtro = filtro_texto.strip().lower()
            articulos = [
                a for a in articulos
                if filtro in a.codigo_inventario.lower() or filtro in a.nombre.lower()
            ]

        self._articulos_filtrados = articulos
        self._pagina_actual = 0

        self._actualizar_kpis(articulos)
        self._renderizar_pagina()

    def _total_paginas(self):
        total = len(self._articulos_filtrados)
        if total == 0:
            return 1
        return (total - 1) // self.TAMANO_PAGINA + 1

    def _pagina_anterior(self):
        if self._pagina_actual > 0:
            self._pagina_actual -= 1
            self._renderizar_pagina()

    def _pagina_siguiente(self):
        if self._pagina_actual < self._total_paginas() - 1:
            self._pagina_actual += 1
            self._renderizar_pagina()

    def _renderizar_pagina(self):
        # Solo se construyen los widgets del bloque de 10 que corresponde
        # a la página actual; el resto de artículos filtrados quedan en
        # self._articulos_filtrados hasta que el usuario avance/retroceda.
        inicio = self._pagina_actual * self.TAMANO_PAGINA
        fin = inicio + self.TAMANO_PAGINA
        articulos_pagina = self._articulos_filtrados[inicio:fin]

        self._articulos = {a.id: a for a in articulos_pagina}

        for hijo in self.lista.winfo_children():
            hijo.destroy()

        nombre_categoria = {v: k for k, v in self._categorias.items()}

        total = len(self._articulos_filtrados)
        total_paginas = self._total_paginas()
        if total == 0:
            self.etiqueta_paginacion.configure(text="Sin artículos")
        else:
            self.etiqueta_paginacion.configure(
                text=f"Mostrando {inicio + 1}–{min(fin, total)} de {total} "
                     f"(página {self._pagina_actual + 1} de {total_paginas})"
            )
        self.boton_pagina_anterior.configure(
            state="normal" if self._pagina_actual > 0 else "disabled"
        )
        self.boton_pagina_siguiente.configure(
            state="normal" if self._pagina_actual < total_paginas - 1 else "disabled"
        )

        for a in articulos_pagina:
            # "Agotado" (sin unidades libres) es un estado derivado del
            # stock, no algo guardado en la BD: solo existen 'disponible'
            # y 'de_baja' en la columna estado_disponibilidad.
            if a.estado_disponibilidad == "de_baja":
                estado_mostrado = "de_baja"
            elif a.cantidad_disponible <= 0:
                estado_mostrado = "agotado"
            else:
                estado_mostrado = "disponible"
            fondo, texto_color = color_badge(estado_mostrado)

            def _celda_estado(celda, estado=estado_mostrado, fondo=fondo, texto_color=texto_color):
                crear_badge(celda, estado.replace("_", " ").title(), fondo, texto_color).place(
                    relx=0, rely=0.5, anchor="w"
                )

            def _celda_stock(celda, art=a):
                ctk.CTkLabel(
                    celda, text=f"{art.cantidad_disponible}/{art.cantidad_total}",
                    text_color=self.c["texto"], font=("Segoe UI", 12)
                ).place(relx=0, rely=0.5, anchor="w")

            def _celda_foto(celda, ruta=a.foto_path):
                imagen = self._miniatura(ruta)
                if imagen:
                    etiqueta = ctk.CTkLabel(celda, image=imagen, text="", corner_radius=6)
                    etiqueta.image = imagen
                else:
                    etiqueta = ctk.CTkLabel(
                        celda, text="—", text_color=self.c["subtext"], font=("Segoe UI", 12)
                    )
                etiqueta.place(relx=0, rely=0.5, anchor="w")

            crear_fila_tabla(
                self.lista, self.c,
                [
                    _celda_foto,
                    a.codigo_inventario,
                    a.nombre,
                    nombre_categoria.get(a.categoria_id, "—"),
                    _celda_estado,
                    _celda_stock,
                    a.ubicacion_actual or "—",
                ],
                self.ANCHOS,
                acciones=[
                    ("Editar",   lambda id_=a.id: self._on_editar(id_)),
                    ("Barras",   lambda id_=a.id: self._on_generar_codigo_barras(id_)),
                    ("Baja",     lambda id_=a.id: self._on_dar_de_baja(id_)),
                    ("Eliminar", lambda id_=a.id: self._on_eliminar(id_)),
                ],
            )

    def _on_editar(self, id_articulo):
        articulo = self._articulos.get(id_articulo)
        if articulo:
            self._abrir_formulario(articulo)

    def _on_dar_de_baja(self, id_articulo):
        if messagebox.askyesno("Confirmar", "¿Dar de baja este artículo?"):
            dar_de_baja(id_articulo)
            self._cargar_articulos()

    def _on_eliminar(self, id_articulo):
        articulo = self._articulos.get(id_articulo)
        nombre = articulo.nombre if articulo else "este artículo"
        if not messagebox.askyesno(
            "Eliminar artículo",
            f"¿Eliminar «{nombre}» de forma permanente?\n\n"
            "Esto borra el artículo y todo su historial de la base de "
            "datos. Esta acción NO se puede deshacer. Si solo quieres "
            "sacarlo de circulación conservando su historial, usa "
            "«Baja» en su lugar."
        ):
            return

        try:
            eliminar_articulo(id_articulo)
        except ValueError as error:
            messagebox.showerror("No se pudo eliminar", str(error))
            return

        self._cargar_articulos(self.entrada_busqueda.get())

    def _on_agregar(self):
        self._abrir_formulario()

    def _on_busqueda_cambio(self, event=None):
        # Filtra en vivo mientras se escribe (búsqueda manual por nombre o
        # código). El Enter del lector de barras se maneja aparte en
        # _on_escaneo para dar feedback si el código no existe.
        if event is not None and event.keysym == "Return":
            return
        self._cargar_articulos(self.entrada_busqueda.get())

    def _on_escaneo(self, event=None):
        texto = self.entrada_busqueda.get().strip()
        if not texto:
            self._cargar_articulos()
            return

        self._cargar_articulos(texto)

        if buscar_articulo_por_codigo(texto) is None and not self._articulos:
            messagebox.showinfo("Sin resultados", f"No se encontró ningún artículo con «{texto}».")

    def _on_limpiar_busqueda(self):
        self.entrada_busqueda.delete(0, "end")
        self._cargar_articulos()

    def _on_generar_codigo_barras(self, id_articulo):
        articulo = self._articulos.get(id_articulo)
        if not articulo:
            return

        try:
            ruta_generada = generar_etiqueta(articulo.codigo_inventario, articulo.nombre)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo generar el código de barras:\n{error}")
            return

        self._mostrar_ventana_codigo_barras(articulo, ruta_generada)

    def _mostrar_ventana_codigo_barras(self, articulo, ruta_generada):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Código de barras — {articulo.codigo_inventario}")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()
        ventana.resizable(False, False)

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(padx=20, pady=20)

        # Se muestra directamente aquí para que se pueda ver (o escanear
        # en pantalla) sin tener que descargar el archivo primero.
        imagen = ctk.CTkImage(Image.open(ruta_generada), size=(320, 130))
        etiqueta_imagen = ctk.CTkLabel(interior, image=imagen, text="")
        etiqueta_imagen.image = imagen
        etiqueta_imagen.pack(pady=(0, 14))

        def _descargar():
            ruta_destino = filedialog.asksaveasfilename(
                title="Descargar código de barras",
                defaultextension=".png",
                initialfile=f"{articulo.codigo_inventario}.png",
                filetypes=[("Imagen PNG", "*.png")],
            )
            if not ruta_destino:
                return
            shutil.copy2(ruta_generada, ruta_destino)
            messagebox.showinfo("Listo", f"Código de barras guardado en:\n{ruta_destino}")

        fila_botones = ctk.CTkFrame(interior, fg_color="transparent")
        fila_botones.pack(fill="x")

        ctk.CTkButton(
            fila_botones, text="Descargar...", command=_descargar, **ESTILO_BOTON_PRIMARIO
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            fila_botones, text="Cerrar", command=ventana.destroy,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    # ------------------------------------------------------------
    # VENTANA DE CATEGORÍAS
    # ------------------------------------------------------------
    def _abrir_categorias(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Categorías")
        ventana.geometry("380x520")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            interior, text="Categorías de artículos",
            font=("Segoe UI", 16, "bold"), text_color=self.c["texto"]
        ).pack(anchor="w", pady=(0, 10))

        lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent", height=300,
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        lista.pack(fill="both", expand=True)

        def _recargar():
            for hijo in lista.winfo_children():
                hijo.destroy()
            for cat in listar_categorias():
                fila = ctk.CTkFrame(lista, fg_color=self.c["fila"], corner_radius=8, height=40)
                fila.pack(fill="x", pady=3)
                fila.pack_propagate(False)

                ctk.CTkLabel(
                    fila, text=cat["nombre"], anchor="w",
                    text_color=self.c["texto"], font=("Segoe UI", 12)
                ).pack(side="left", fill="both", expand=True, padx=(10, 0))

                ctk.CTkButton(
                    fila, text="Eliminar", width=64, height=26, corner_radius=8,
                    font=("Segoe UI", 11, "bold"), fg_color="transparent",
                    text_color=COLORES["error"], hover_color=self.c["card_inner"],
                    command=lambda c=cat: _eliminar(c)
                ).pack(side="right", padx=(0, 8))

                ctk.CTkButton(
                    fila, text="Editar", width=54, height=26, corner_radius=8,
                    font=("Segoe UI", 11, "bold"), fg_color="transparent",
                    text_color=self.c["link"], hover_color=self.c["card_inner"],
                    command=lambda c=cat: _editar(c)
                ).pack(side="right", padx=(0, 4))

        def _eliminar(cat):
            if not messagebox.askyesno("Confirmar", f"¿Eliminar la categoría '{cat['nombre']}'?"):
                return
            try:
                eliminar_categoria(cat["id"])
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return
            _recargar()
            self._refrescar_categorias()
            self._cargar_articulos()

        def _editar(cat):
            entrada_nombre.delete(0, "end")
            entrada_nombre.insert(0, cat["nombre"])
            entrada_desc.delete(0, "end")
            entrada_desc.insert(0, cat.get("descripcion") or "")
            edicion["id"] = cat["id"]
            boton_guardar.configure(text="Guardar cambios")

        edicion = {"id": None}

        ctk.CTkLabel(
            interior, text="Nombre", anchor="w",
            text_color=self.c["subtext"], font=("Segoe UI", 11)
        ).pack(fill="x", pady=(16, 2))
        entrada_nombre = ctk.CTkEntry(interior)
        entrada_nombre.pack(fill="x")

        ctk.CTkLabel(
            interior, text="Descripción (opcional)", anchor="w",
            text_color=self.c["subtext"], font=("Segoe UI", 11)
        ).pack(fill="x", pady=(8, 2))
        entrada_desc = ctk.CTkEntry(interior)
        entrada_desc.pack(fill="x")

        def _guardar_categoria():
            nombre = entrada_nombre.get().strip()
            descripcion = entrada_desc.get().strip() or None

            if not campo_no_vacio(nombre):
                messagebox.showerror("Error", "El nombre de la categoría es obligatorio.")
                return

            if edicion["id"] is not None:
                editar_categoria(edicion["id"], nombre, descripcion)
            else:
                agregar_categoria(nombre, descripcion)

            entrada_nombre.delete(0, "end")
            entrada_desc.delete(0, "end")
            edicion["id"] = None
            boton_guardar.configure(text="+  Agregar categoría")
            _recargar()
            self._refrescar_categorias()
            self._cargar_articulos()

        boton_guardar = ctk.CTkButton(
            interior, text="+  Agregar categoría", command=_guardar_categoria,
            **ESTILO_BOTON_PRIMARIO
        )
        boton_guardar.pack(fill="x", pady=(12, 0))

        _recargar()

    # ------------------------------------------------------------
    # FORMULARIO (agregar / editar)
    # ------------------------------------------------------------
    def _abrir_formulario(self, articulo=None):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar artículo" if articulo else "Agregar artículo")
        ventana.minsize(680, 520)
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        # Grid de 2 columnas iguales (mismo patrón que el formulario de
        # "Nuevo préstamo" en asignacion_view.py): cada campo vive en su
        # propia celda (frame con label arriba + input abajo) en vez de
        # apilarse todos verticalmente con pack(), que es lo que forzaba
        # el modal angosto y alargado de antes.
        interior.grid_columnconfigure(0, weight=1, uniform="col", minsize=300)
        interior.grid_columnconfigure(1, weight=1, uniform="col", minsize=300)

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

        # Fila 0: Prefijo (solo al agregar) + Nombre. Si se está editando
        # no hay prefijo, así que "Nombre" ocupa las dos columnas.
        if not articulo:
            _campo_entry(0, 0, "Prefijo (TEC/OFI/AUD)", "TEC")
            _campo_entry(0, 1, "Nombre", articulo.nombre if articulo else "")
        else:
            _campo_entry(0, 0, "Nombre", articulo.nombre, colspan=2)

        # Fila 1: al agregar, código de barras (opcional) + cantidad en
        # stock; al editar, solo la cantidad en stock (el código ya no se
        # toca). Cada fila de articulos es un TIPO de artículo con un
        # contador de unidades (cantidad_total/cantidad_disponible), no
        # una fila por unidad física.
        fila_extra = 1
        if not articulo:
            _campo_entry(1, 0, "Código de barras (opcional, déjalo vacío para generarlo)", "")
            _campo_entry(1, 1, "Cantidad en stock (vacío = 1)", "")
        else:
            _campo_entry(1, 0, "Cantidad en stock (vacío = 1)", str(articulo.cantidad_total), colspan=2)

        # Fila 1+extra: Categoría (+ botón "+") | Marca
        frame_categoria = _celda(1 + fila_extra, 0)
        ctk.CTkLabel(frame_categoria, text="Categoría", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
        fila_categoria = ctk.CTkFrame(frame_categoria, fg_color="transparent")
        fila_categoria.pack(fill="x")

        combo_categoria = ctk.CTkComboBox(fila_categoria, values=list(self._categorias.keys()), state="readonly")
        if articulo:
            nombre_cat = next((n for n, i in self._categorias.items() if i == articulo.categoria_id), "")
            combo_categoria.set(nombre_cat)
        combo_categoria.pack(side="left", fill="x", expand=True)

        def _agregar_categoria_rapida():
            ventana_cat = ctk.CTkToplevel(ventana)
            ventana_cat.title("Nueva categoría")
            ventana_cat.geometry("300x230")
            ventana_cat.configure(fg_color=self.c["fondo"])
            ventana_cat.transient(ventana)
            ventana_cat.grab_set()

            tarjeta_cat = crear_card(ventana_cat, self.c)
            tarjeta_cat.pack(fill="both", expand=True, padx=14, pady=14)
            interior_cat = ctk.CTkFrame(tarjeta_cat, fg_color="transparent")
            interior_cat.pack(fill="both", expand=True, padx=14, pady=14)

            ctk.CTkLabel(interior_cat, text="Nombre", anchor="w",
                         text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
            entrada_nombre_cat = ctk.CTkEntry(interior_cat)
            entrada_nombre_cat.pack(fill="x")

            ctk.CTkLabel(interior_cat, text="Descripción (opcional)", anchor="w",
                         text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))
            entrada_desc_cat = ctk.CTkEntry(interior_cat)
            entrada_desc_cat.pack(fill="x")

            def _guardar_categoria_rapida():
                nombre_cat = entrada_nombre_cat.get().strip()
                if not campo_no_vacio(nombre_cat):
                    messagebox.showerror("Error", "El nombre de la categoría es obligatorio.")
                    return

                agregar_categoria(nombre_cat, entrada_desc_cat.get().strip() or None)
                self._refrescar_categorias()
                combo_categoria.configure(values=list(self._categorias.keys()))
                combo_categoria.set(nombre_cat)
                ventana_cat.destroy()

            ctk.CTkButton(interior_cat, text="Guardar categoría", command=_guardar_categoria_rapida,
                          **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(16, 0))

        ctk.CTkButton(
            fila_categoria, text="+", width=32, command=_agregar_categoria_rapida,
            **ESTILO_BOTON_SECUNDARIO
        ).pack(side="left", padx=(8, 0))

        _campo_entry(1 + fila_extra, 1, "Marca", articulo.marca if articulo else "")

        # Fila 2+extra: Modelo | Serie
        _campo_entry(2 + fila_extra, 0, "Modelo", articulo.modelo if articulo else "")
        _campo_entry(2 + fila_extra, 1, "Serie", articulo.serie if articulo else "")

        # Fila 3+extra: Ubicación | Fecha de adquisición (mismo widget de
        # calendario que "Nuevo préstamo" en asignacion_view.py, en vez de
        # un texto libre que había que escribir a mano).
        _campo_entry(3 + fila_extra, 0, "Ubicación", articulo.ubicacion_actual if articulo else "")

        frame_fecha = _celda(3 + fila_extra, 1)
        ctk.CTkLabel(frame_fecha, text="Fecha de adquisición", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        fecha_inicial = articulo.fecha_adquisicion if articulo and articulo.fecha_adquisicion else date.today()
        calendario_adquisicion = Calendar(
            frame_fecha,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            year=fecha_inicial.year, month=fecha_inicial.month, day=fecha_inicial.day,
            maxdate=date.today(),
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
        calendario_adquisicion.pack(fill="x", ipady=2)

        # Fila 4+extra: Estado físico (la otra columna queda como espaciador)
        frame_estado = _celda(4 + fila_extra, 0)
        ctk.CTkLabel(frame_estado, text="Estado físico", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))
        combo_estado = ctk.CTkComboBox(frame_estado, values=["bueno", "regular", "dañado"], state="readonly")
        combo_estado.set(articulo.estado_fisico if articulo else "bueno")
        combo_estado.pack(fill="x")

        # Fila 5+extra: Foto del artículo (ancho completo)
        frame_foto = _celda(5 + fila_extra, 0, colspan=2)
        ctk.CTkLabel(frame_foto, text="Foto", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(0, 2))

        foto_estado = {"path": articulo.foto_path if articulo else None}

        fila_foto = ctk.CTkFrame(frame_foto, fg_color="transparent")
        fila_foto.pack(fill="x")

        vista_previa = ctk.CTkLabel(
            fila_foto, text="Sin foto", width=64, height=64, corner_radius=8,
            fg_color=self.c["card_inner"], text_color=self.c["subtext"],
            font=("Segoe UI", 10),
        )
        vista_previa.pack(side="left")

        def _mostrar_previa(ruta):
            if ruta and os.path.isfile(ruta):
                try:
                    imagen = ctk.CTkImage(Image.open(ruta), size=(64, 64))
                    vista_previa.configure(image=imagen, text="")
                    vista_previa.image = imagen
                    return
                except Exception:
                    pass
            vista_previa.configure(image=None, text="Sin foto")
            vista_previa.image = None

        def _seleccionar_foto():
            ruta_origen = filedialog.askopenfilename(
                title="Seleccionar foto del artículo",
                filetypes=[("Imágenes", " ".join(f"*{ext}" for ext in EXTENSIONES_FOTO))],
            )
            if not ruta_origen:
                return

            os.makedirs(CARPETA_FOTOS, exist_ok=True)
            extension = os.path.splitext(ruta_origen)[1].lower()
            nombre_archivo = f"{uuid.uuid4().hex}{extension}"
            ruta_destino = os.path.join(CARPETA_FOTOS, nombre_archivo)
            shutil.copy2(ruta_origen, ruta_destino)

            foto_estado["path"] = ruta_destino
            _mostrar_previa(ruta_destino)

        def _abrir_camara():
            def _al_capturar(ruta):
                foto_estado["path"] = ruta
                _mostrar_previa(ruta)

            abrir_ventana_camara(
                ventana, self.c, "Tomar foto del artículo",
                CARPETA_FOTOS, _al_capturar, ESTILO_BOTON_PRIMARIO
            )

        botones_foto = ctk.CTkFrame(fila_foto, fg_color="transparent")
        botones_foto.pack(side="left", padx=(10, 0), fill="y")

        ctk.CTkButton(
            botones_foto, text="Seleccionar foto...", height=28,
            command=_seleccionar_foto, **ESTILO_BOTON_SECUNDARIO
        ).pack(anchor="w")

        ctk.CTkButton(
            botones_foto, text="Tomar foto...", height=28,
            command=_abrir_camara, **ESTILO_BOTON_SECUNDARIO
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            botones_foto, text="Quitar foto", height=24, width=90,
            fg_color="transparent", text_color=self.c["subtext"],
            hover_color=self.c["card_inner"],
            command=lambda: (foto_estado.update(path=None), _mostrar_previa(None))
        ).pack(anchor="w", pady=(4, 0))

        _mostrar_previa(foto_estado["path"])

        def _guardar():
            nombre = campos["Nombre"].get().strip()
            categoria_nombre = combo_categoria.get()
            fecha = calendario_adquisicion.get_date()

            if not campo_no_vacio(nombre):
                messagebox.showerror("Error", "El nombre es obligatorio.")
                return
            if categoria_nombre not in self._categorias:
                messagebox.showerror("Error", "Selecciona una categoría válida.")
                return

            cantidad_texto = campos["Cantidad en stock (vacío = 1)"].get().strip()
            cantidad_total = 1
            if cantidad_texto:
                if not cantidad_texto.isdigit() or int(cantidad_texto) < 1:
                    messagebox.showerror("Error", "La cantidad en stock debe ser un número entero de 1 o más.")
                    return
                cantidad_total = int(cantidad_texto)

            datos = {
                "nombre": nombre,
                "categoria_id": self._categorias[categoria_nombre],
                "marca": campos["Marca"].get().strip() or None,
                "modelo": campos["Modelo"].get().strip() or None,
                "serie": campos["Serie"].get().strip() or None,
                "foto_path": foto_estado["path"],
                "estado_fisico": combo_estado.get(),
                "fecha_adquisicion": fecha,
                "ubicacion_actual": campos["Ubicación"].get().strip() or None,
                "cantidad_total": cantidad_total,
            }

            try:
                if articulo:
                    editar_articulo(articulo.id, datos)
                else:
                    datos["prefijo_codigo"] = campos["Prefijo (TEC/OFI/AUD)"].get().strip().upper() or "TEC"
                    datos["codigo_manual"] = campos["Código de barras (opcional, déjalo vacío para generarlo)"].get().strip()
                    agregar_articulo(datos)
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return

            ventana.destroy()
            self._cargar_articulos()

        # Fila 6+extra: botón de guardar (ancho completo)
        frame_boton = _celda(6 + fila_extra, 0, colspan=2)
        ctk.CTkButton(frame_boton, text="Guardar", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(6, 0))

        # Ajusta la ventana al tamaño real que pide el contenido (evita que
        # algún campo quede cortado sin scroll) y respeta un ancho mínimo
        # para que el modal quede ancho de 2 columnas en vez de angosto.
        ventana.update_idletasks()
        alto = tarjeta.winfo_reqheight() + 32
        ancho = max(720, tarjeta.winfo_reqwidth() + 32)
        ventana.geometry(f"{ancho}x{alto}")
