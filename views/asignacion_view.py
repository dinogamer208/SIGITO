"""
views/asignacion_view.py — Pantalla de asignaciones (préstamos y devoluciones).

Frame embebido dentro del área de contenido del Dashboard (se muestra
al navegar desde el sidebar, reemplazando la vista anterior): arma su
layout con los colores de views/tema.py y los componentes compartidos
de views/componentes.py (tarjetas KPI, badges, tabla).
"""

import customtkinter as ctk
from tkinter import messagebox

from controllers.asignacion_controller import (
    listar_asignaciones_activas, registrar_prestamo, registrar_devolucion
)
from controllers.inventario_controller import listar_articulos
from controllers.auth_controller import listar_profesores
from utils.validaciones import correo_valido, fecha_valida
from views.tema import COLORES, colores_dashboard, ESTILO_BOTON_PRIMARIO
from views.componentes import (
    crear_card, crear_encabezado, crear_kpi_card,
    crear_encabezado_tabla, crear_fila_tabla, crear_badge
)


class AsignacionView(ctk.CTkFrame):

    ANCHOS = (170, 80, 140, 140, 100)
    _COLORES_AVATAR = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B",
                        "#EF4444", "#06B6D4", "#EC4899", "#6366F1"]

    def __init__(self, master, usuario=None):
        super().__init__(master, fg_color="transparent")

        self.usuario = usuario
        self.c = colores_dashboard()

        self._construir_layout()
        self._cargar_asignaciones()

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
            ["Alumno", "Sección", "Salida", "Devolución esperada", "Estado"],
            self.ANCHOS
        )

        self.lista = ctk.CTkScrollableFrame(
            interior, fg_color="transparent",
            scrollbar_button_color=self.c["borde"],
            scrollbar_button_hover_color=COLORES["dash_hover_claro"],
        )
        self.lista.pack(fill="both", expand=True)

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
                    a.hora_salida.strftime("%Y-%m-%d %H:%M"),
                    a.hora_estimada_devolucion.strftime("%Y-%m-%d %H:%M"),
                    _celda_estado,
                ],
                self.ANCHOS,
                acciones=[("Devolver", lambda id_=a.id: self._on_devolucion(id_))],
            )

    def _on_devolucion(self, asignacion_id):
        if not messagebox.askyesno("Confirmar", "¿Registrar la devolución de este equipo?"):
            return
        usuario_id = self.usuario.id if self.usuario else None
        registrar_devolucion(asignacion_id, usuario_id)
        self._cargar_asignaciones()

    # ------------------------------------------------------------
    # FORMULARIO — nuevo préstamo
    # ------------------------------------------------------------
    def _on_nuevo_prestamo(self):
        articulos_disponibles = listar_articulos(estado_disponibilidad="disponible")
        profesores = listar_profesores()

        if not articulos_disponibles:
            messagebox.showwarning("Aviso", "No hay artículos disponibles para prestar.")
            return
        if not profesores:
            messagebox.showwarning("Aviso", "No hay profesores autorizados registrados.")
            return

        ventana = ctk.CTkToplevel(self)
        ventana.title("Nuevo préstamo")
        ventana.geometry("400x640")
        ventana.configure(fg_color=self.c["fondo"])
        ventana.transient(self)
        ventana.grab_set()

        tarjeta = crear_card(ventana, self.c)
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        interior = ctk.CTkFrame(tarjeta, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=16, pady=16)

        mapa_articulos = {f"{a.codigo_inventario} - {a.nombre}": a.id for a in articulos_disponibles}
        mapa_profesores = {p["nombre_completo"]: p["id"] for p in profesores}

        campos = {}

        def _etiqueta(texto):
            ctk.CTkLabel(interior, text=texto, anchor="w",
                         text_color=self.c["subtext"], font=("Segoe UI", 11)).pack(fill="x", pady=(8, 2))

        def _fila(etiqueta, valor_inicial=""):
            _etiqueta(etiqueta)
            entrada = ctk.CTkEntry(interior)
            entrada.insert(0, valor_inicial)
            entrada.pack(fill="x")
            campos[etiqueta] = entrada

        _etiqueta("Artículo")
        combo_articulo = ctk.CTkComboBox(interior, values=list(mapa_articulos.keys()), state="readonly")
        combo_articulo.pack(fill="x")

        _fila("Nombre completo del alumno")
        _fila("Sección")
        _fila("Año")
        _fila("Teléfono")
        _fila("Correo")

        _etiqueta("Profesor que autoriza")
        combo_profesor = ctk.CTkComboBox(interior, values=list(mapa_profesores.keys()), state="readonly")
        combo_profesor.pack(fill="x")

        _fila("Devolución esperada (YYYY-MM-DD HH:MM)")

        def _guardar():
            nombre = campos["Nombre completo del alumno"].get().strip()
            seccion = campos["Sección"].get().strip()
            anio = campos["Año"].get().strip()
            telefono = campos["Teléfono"].get().strip()
            correo = campos["Correo"].get().strip()
            hora_dev = campos["Devolución esperada (YYYY-MM-DD HH:MM)"].get().strip()

            if not all([nombre, seccion, anio, telefono, correo, combo_articulo.get(), combo_profesor.get()]):
                messagebox.showerror("Error", "Todos los campos son obligatorios.")
                return
            if not correo_valido(correo):
                messagebox.showerror("Error", "Correo inválido.")
                return
            if not fecha_valida(hora_dev, "%Y-%m-%d %H:%M"):
                messagebox.showerror("Error", "Fecha/hora inválida, usa el formato YYYY-MM-DD HH:MM.")
                return

            try:
                registrar_prestamo(
                    articulo_id=mapa_articulos[combo_articulo.get()],
                    nombre_completo=nombre,
                    seccion=seccion,
                    anio=anio,
                    telefono=telefono,
                    correo=correo,
                    profesor_autoriza_id=mapa_profesores[combo_profesor.get()],
                    hora_estimada_devolucion=hora_dev,
                    usuario_registro_id=self.usuario.id if self.usuario else None,
                )
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return

            ventana.destroy()
            self._cargar_asignaciones()

        ctk.CTkButton(interior, text="Registrar préstamo", command=_guardar,
                      **ESTILO_BOTON_PRIMARIO).pack(fill="x", pady=(16, 0))
