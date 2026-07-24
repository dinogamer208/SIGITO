"""
views/inventario_view.py — Pantalla de inventario.

Ventana propia (ctk.CTkToplevel), misma lógica de clase que Dashboard:
arma su layout con los colores de views/tema.py y los componentes
compartidos de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import customtkinter as ctk
from tkinter import messagebox

from controllers.inventario_controller import (
    listar_articulos, agregar_articulo, editar_articulo, dar_de_baja,
    listar_categorias
)
from utils.validaciones import campo_no_vacio, fecha_valida
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO, color_badge
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card,
    crear_encabezado_tabla, crear_fila_tabla, crear_badge
)


class InventarioView(ctk.CTkToplevel):

    ANCHOS = (95, 190, 120, 110, 120)

    def __init__(self, master):
        super().__init__(master)

        self.c = colores_dashboard()
        self._categorias = {cat["nombre"]: cat["id"] for cat in listar_categorias()}

        self.title("Inventario")
        self.geometry("1080x640")
        self.minsize(820, 520)
        self.configure(fg_color=self.c["fondo"])

        self._construir_layout()
        self._cargar_articulos()

        self.transient(master)
        self.grab_set()

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

        self.fila_kpis = ctk.CTkFrame(contenedor, fg_color="transparent")
        self.fila_kpis.pack(fill="x", pady=(18, 16))

        tarjeta = crear_card(contenedor, self.c)
        tarjeta.pack(fill="both", expand=True)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=14, pady=14)

        crear_encabezado_tabla(
            interior, self.c,
            ["Código", "Nombre", "Categoría", "Estado", "Ubicación"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

    def _actualizar_kpis(self, articulos):
        for hijo in self.fila_kpis.winfo_children():
            hijo.destroy()

        total = len(articulos)
        disponibles = sum(1 for a in articulos if a.estado_disponibilidad == "disponible")
        prestados = sum(1 for a in articulos if a.estado_disponibilidad == "prestado")
        de_baja = sum(1 for a in articulos if a.estado_disponibilidad == "de_baja")

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
    def _cargar_articulos(self):
        articulos = listar_articulos()
        self._articulos = {a.id: a for a in articulos}

        self._actualizar_kpis(articulos)

        for hijo in self.lista.winfo_children():
            hijo.destroy()

        nombre_categoria = {v: k for k, v in self._categorias.items()}

        for a in articulos:
            fondo, texto_color = color_badge(a.estado_disponibilidad)

            def _celda_estado(celda, estado=a.estado_disponibilidad, fondo=fondo, texto_color=texto_color):
                crear_badge(celda, estado.replace("_", " ").title(), fondo, texto_color).place(
                    relx=0, rely=0.5, anchor="w"
                )

            crear_fila_tabla(
                self.lista, self.c,
                [
                    a.codigo_inventario,
                    a.nombre,
                    nombre_categoria.get(a.categoria_id, "—"),
                    _celda_estado,
                    a.ubicacion_actual or "—",
                ],
                self.ANCHOS,
                acciones=[
                    ("Editar", lambda id_=a.id: self._on_editar(id_)),
                    ("Baja",   lambda id_=a.id: self._on_dar_de_baja(id_)),
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

    def _on_agregar(self):
        self._abrir_formulario()

    # ------------------------------------------------------------
    # FORMULARIO (agregar / editar)
    # ------------------------------------------------------------
    def _abrir_formulario(self, articulo=None):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Editar artículo" if articulo else "Agregar artículo")
        ventana.geometry("400x740")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        campos = {}

        def _fila(etiqueta, valor_inicial=""):
            ctk.CTkLabel(interior, text=etiqueta, anchor="w",
                         text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))
            entrada = ctk.CTkEntry(interior)
            entrada.insert(0, valor_inicial)
            entrada.pack(fill="x")
            campos[etiqueta] = entrada

        if not articulo:
            _fila("Prefijo (TEC/OFI/AUD)", "TEC")
        _fila("Nombre", articulo.nombre if articulo else "")

        ctk.CTkLabel(interior, text="Categoría", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))
        combo_categoria = ctk.CTkComboBox(interior, values=list(self._categorias.keys()), state="readonly")
        if articulo:
            nombre_cat = next((n for n, i in self._categorias.items() if i == articulo.categoria_id), "")
            combo_categoria.set(nombre_cat)
        combo_categoria.pack(fill="x")

        _fila("Marca", articulo.marca if articulo else "")
        _fila("Modelo", articulo.modelo if articulo else "")
        _fila("Serie", articulo.serie if articulo else "")
        _fila("Ubicación", articulo.ubicacion_actual if articulo else "")
        _fila("Fecha adquisición (YYYY-MM-DD)",
              str(articulo.fecha_adquisicion) if articulo and articulo.fecha_adquisicion else "")

        ctk.CTkLabel(interior, text="Estado físico", anchor="w",
                     text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))
        combo_estado = ctk.CTkComboBox(interior, values=["bueno", "regular", "dañado"], state="readonly")
        combo_estado.set(articulo.estado_fisico if articulo else "bueno")
        combo_estado.pack(fill="x")

        def _guardar():
            nombre = campos["Nombre"].get().strip()
            categoria_nombre = combo_categoria.get()
            fecha = campos["Fecha adquisición (YYYY-MM-DD)"].get().strip()

            if not campo_no_vacio(nombre):
                messagebox.showerror("Error", "El nombre es obligatorio.")
                return
            if categoria_nombre not in self._categorias:
                messagebox.showerror("Error", "Selecciona una categoría válida.")
                return
            if fecha and not fecha_valida(fecha):
                messagebox.showerror("Error", "Fecha inválida, usa el formato YYYY-MM-DD.")
                return

            datos = {
                "nombre": nombre,
                "categoria_id": self._categorias[categoria_nombre],
                "marca": campos["Marca"].get().strip() or None,
                "modelo": campos["Modelo"].get().strip() or None,
                "serie": campos["Serie"].get().strip() or None,
                "foto_path": None,
                "estado_fisico": combo_estado.get(),
                "fecha_adquisicion": fecha or None,
                "ubicacion_actual": campos["Ubicación"].get().strip() or None,
            }

            if articulo:
                editar_articulo(articulo.id, datos)
            else:
                datos["prefijo_codigo"] = campos["Prefijo (TEC/OFI/AUD)"].get().strip().upper() or "TEC"
                agregar_articulo(datos)

            ventana.destroy()
            self._cargar_articulos()

        ctk.CTkButton(interior, text="Guardar", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(16, 0))
