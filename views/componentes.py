"""
views/componentes.py
----------------------
Widgets reutilizables para las ventanas internas del Dashboard
(Inventario, Asignaciones, Reportes, Usuarios), siguiendo el mismo
lenguaje visual de dashboard_view.py (tarjetas redondeadas, franja de
color superior en los KPI, badges de estado) y el layout de referencia
de los mockups de Stitch (KPI cards con acento de color + tabla
principal con badges y columna de acciones).

Todas las vistas internas importan de aquí en vez de reconstruir
tarjetas/badges a mano, igual que todas importan colores desde tema.py.
"""

import os
import uuid

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont

from utils.sistema import area_de_trabajo


def listar_camaras_disponibles(max_indices=5):
    """
    Prueba los índices 0..max_indices-1 con DirectShow y devuelve los que
    sí abren (OpenCV no expone nombres de dispositivo por índice, así que
    se listan como "Cámara 0", "Cámara 1", etc.).
    """
    import cv2  # import local: pesado, solo se necesita al usar la cámara

    disponibles = []
    for indice in range(max_indices):
        captura = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
        if captura.isOpened():
            disponibles.append(indice)
        captura.release()
    return disponibles


def abrir_ventana_camara(padre, colores, titulo, carpeta_destino, on_capturada, estilo_boton_primario):
    """
    Ventana modal para tomar una foto con la cámara, con selector de
    cámara cuando hay más de una conectada (ej. webcam integrada +
    cámara USB). Usada por Asignaciones (foto del alumno) e Inventario
    (foto del artículo) — ver views/asignacion_view.py y
    views/inventario_view.py.

    `on_capturada(ruta)` se llama con la ruta del PNG guardado en
    `carpeta_destino` cuando el usuario presiona "Capturar".
    """
    import cv2  # import local: pesado, solo se necesita al tomar la foto

    camaras = listar_camaras_disponibles()
    if not camaras:
        messagebox.showerror("Error", "No se detectó ninguna cámara conectada.")
        return

    estado = {"indice": camaras[0], "captura": None, "activo": True}

    def _abrir_indice(indice):
        if estado["captura"] is not None:
            estado["captura"].release()
        estado["indice"] = indice
        estado["captura"] = cv2.VideoCapture(indice, cv2.CAP_DSHOW)

    _abrir_indice(camaras[0])

    camara_ventana = ctk.CTkToplevel(padre)
    centrar_ventana(camara_ventana)
    camara_ventana.title(titulo)
    camara_ventana.configure(fg_color=colores["fondo"])
    camara_ventana.transient(padre)
    camara_ventana.grab_set()
    camara_ventana.resizable(False, False)

    if len(camaras) > 1:
        fila_selector = ctk.CTkFrame(camara_ventana, fg_color="transparent")
        fila_selector.pack(fill="x", padx=16, pady=(16, 0))
        ctk.CTkLabel(fila_selector, text="Cámara:", text_color=colores["subtext"],
                     font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))

        etiquetas = {f"Cámara {i}": i for i in camaras}

        def _cambiar_camara(etiqueta):
            _abrir_indice(etiquetas[etiqueta])

        ctk.CTkOptionMenu(
            fila_selector, values=list(etiquetas.keys()),
            command=_cambiar_camara, width=140,
        ).pack(side="left")

    etiqueta_video = ctk.CTkLabel(
        camara_ventana, text="Abriendo cámara...", width=480, height=360,
        fg_color=colores["card_inner"],
    )
    etiqueta_video.pack(padx=16, pady=16)
    etiqueta_video._ultimo_frame = None

    def _cerrar():
        estado["activo"] = False
        if estado["captura"] is not None:
            estado["captura"].release()
        camara_ventana.destroy()

    def _actualizar_frame():
        if not estado["activo"]:
            return
        ok, frame = estado["captura"].read()
        if ok:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imagen_ctk = ctk.CTkImage(Image.fromarray(frame_rgb), size=(480, 360))
            etiqueta_video.configure(image=imagen_ctk, text="")
            etiqueta_video.image = imagen_ctk
            etiqueta_video._ultimo_frame = frame
        camara_ventana.after(30, _actualizar_frame)

    def _capturar():
        frame = etiqueta_video._ultimo_frame
        if frame is None:
            messagebox.showerror("Error", "No se pudo leer la cámara.")
            return
        os.makedirs(carpeta_destino, exist_ok=True)
        ruta = os.path.join(carpeta_destino, f"{uuid.uuid4().hex}.png")
        cv2.imwrite(ruta, frame)
        on_capturada(ruta)
        _cerrar()

    camara_ventana.protocol("WM_DELETE_WINDOW", _cerrar)

    botones_camara = ctk.CTkFrame(camara_ventana, fg_color="transparent")
    botones_camara.pack(fill="x", padx=16, pady=(0, 16))
    ctk.CTkButton(botones_camara, text="Capturar", command=_capturar,
                  **estilo_boton_primario).pack(side="left", expand=True, fill="x", padx=(0, 6))
    ctk.CTkButton(botones_camara, text="Cancelar", command=_cerrar,
                  fg_color="transparent", text_color=colores["subtext"],
                  hover_color=colores["card_inner"]).pack(side="left", expand=True, fill="x", padx=(6, 0))

    _actualizar_frame()


def crear_kpi_card(padre, colores, numero, titulo, color_acento):
    """
    Tarjeta KPI con franja de color superior (patrón usado en todas las
    pantallas de los mockups de Stitch: Total, Prestados, Vencidos, etc.)
    """
    contenedor = ctk.CTkFrame(padre, fg_color="transparent")

    ctk.CTkFrame(contenedor, height=3, fg_color=color_acento,
                 corner_radius=0).pack(fill="x")

    cuerpo = ctk.CTkFrame(
        contenedor,
        fg_color=colores["card"],
        corner_radius=14,
        border_width=1,
        border_color=colores["borde"],
    )
    cuerpo.pack(fill="both", expand=True)

    ctk.CTkLabel(
        cuerpo, text=titulo.upper(),
        font=("Segoe UI", 11, "bold"),
        text_color=colores["subtext"]
    ).pack(anchor="w", padx=16, pady=(14, 0))

    ctk.CTkLabel(
        cuerpo, text=str(numero),
        font=("Segoe UI", 26, "bold"),
        text_color=colores["texto"]
    ).pack(anchor="w", padx=16, pady=(2, 14))

    return contenedor


def crear_campo_password(padre, colores, **kwargs_entry):
    """
    Campo de contraseña (CTkEntry con show="*") con un botón "Ver" al
    lado para mostrar/ocultar lo que se está escribiendo, sin depender
    de otra librería. Devuelve (frame, entry): empacar `frame` con
    pack(fill="x") y usar `entry` para .get()/.delete()/.bind() como
    cualquier CTkEntry normal.
    """
    frame = ctk.CTkFrame(padre, fg_color="transparent")

    entry = ctk.CTkEntry(frame, show="*", **kwargs_entry)
    entry.pack(side="left", fill="x", expand=True)

    estado = {"visible": False}

    def _toggle():
        estado["visible"] = not estado["visible"]
        entry.configure(show="" if estado["visible"] else "*")
        boton.configure(text="Ocultar" if estado["visible"] else "Ver")

    boton = ctk.CTkButton(
        frame, text="Ver", width=56, height=kwargs_entry.get("height", 28),
        command=_toggle, fg_color="transparent", border_width=1,
        border_color=colores["borde"], text_color=colores["subtext"],
        hover_color=colores["card_inner"], font=("Segoe UI", 11),
    )
    boton.pack(side="left", padx=(6, 0))

    return frame, entry


def centrar_ventana(ventana, duracion_ms=1000):
    """
    Centra una ventana emergente (CTkToplevel) en la pantalla. Llamar
    justo después de crearla.

    Mientras se arma, una ventana cambia de tamaño varias veces (el
    contenido se acomoda, CustomTkinter aplica el zoom de Windows, la
    propia vista fija su tamaño al final...), así que durante su primer
    segundo se vuelve a centrar cada vez que cambia de tamaño. Hasta el
    primer centrado queda transparente, para que no se vea saltar desde
    la esquina.
    """
    try:
        ventana.attributes("-alpha", 0.0)
    except Exception:  # noqa: BLE001 - algunos sistemas no soportan -alpha
        pass

    estado = {"activo": True, "tamano": None}

    def _centrar(forzar=False):
        if not estado["activo"] or not ventana.winfo_exists():
            return
        ventana.update_idletasks()
        ancho = ventana.winfo_width() if ventana.winfo_width() > 1 else ventana.winfo_reqwidth()
        alto = ventana.winfo_height() if ventana.winfo_height() > 1 else ventana.winfo_reqheight()
        if not forzar and (ancho, alto) == estado["tamano"]:
            return  # solo se movió (p. ej. por el propio centrado)
        estado["tamano"] = (ancho, alto)

        area_x, area_y, area_ancho, area_alto = area_de_trabajo(ventana)
        x = area_x + max((area_ancho - ancho) // 2, 0)
        y = area_y + max((area_alto - alto) // 2, 0)
        # Solo la posición: CustomTkinter no escala x/y, y así no se toca
        # el tamaño que haya fijado la ventana.
        ventana.geometry(f"+{x}+{y}")
        try:
            ventana.attributes("-alpha", 1.0)
        except Exception:  # noqa: BLE001
            pass

    def _al_cambiar(event):
        if event.widget is ventana:
            _centrar()

    # No se hace unbind al terminar: en algunas versiones de Python
    # unbind(secuencia, id) borra también el <Configure> de CustomTkinter.
    ventana.bind("<Configure>", _al_cambiar, add="+")

    def _terminar():
        _centrar(forzar=True)
        estado["activo"] = False

    ventana.after(60, lambda: _centrar(forzar=True))
    ventana.after(duracion_ms, _terminar)

    # Esc cierra la ventana, igual que la X: si la ventana tiene su propio
    # manejador de cierre (p. ej. la cámara, que libera el dispositivo), se usa ese.
    def _cerrar(_event=None):
        comando = ventana.protocol("WM_DELETE_WINDOW")
        if comando:
            ventana.tk.call(comando)
        else:
            ventana.destroy()

    ventana.bind("<Escape>", _cerrar, add="+")


# Avatares ya dibujados, por (color, iniciales, tamaño): se reusan entre filas.
_AVATARES = {}


def imagen_avatar(color, iniciales, tamano=30):
    """
    Círculo de color con las iniciales, como CTkImage. Se dibuja como
    imagen (con suavizado) en vez de un CTkFrame redondeado con una
    etiqueta encima: a estos tamaños y con el zoom de Windows, el frame
    no quedaba redondo y la etiqueta se salía por abajo del círculo.
    """
    clave = (color, iniciales, tamano)
    if clave not in _AVATARES:
        escala = 4  # se dibuja 4 veces más grande y CTkImage lo reduce: bordes lisos
        lado = tamano * escala
        imagen = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        dibujo = ImageDraw.Draw(imagen)
        dibujo.ellipse((0, 0, lado - 1, lado - 1), fill=color)
        fuente = None
        for archivo in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
            try:
                fuente = ImageFont.truetype(archivo, int(lado * 0.38))
                break
            except OSError:
                continue
        dibujo.text((lado / 2, lado / 2), iniciales, fill="#FFFFFF",
                    font=fuente or ImageFont.load_default(), anchor="mm")
        _AVATARES[clave] = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(tamano, tamano))
    return _AVATARES[clave]


def crear_badge(padre, texto, fondo, texto_color):
    """Chip redondeado para estados (Disponible, Prestado, Vencido...)."""
    return ctk.CTkLabel(
        padre, text=f"  {texto}  ",
        font=("Segoe UI", 10, "bold"),
        fg_color=fondo, text_color=texto_color,
        corner_radius=10,
    )


def crear_card(padre, colores, **kwargs):
    """Tarjeta base (fondo, borde y radio consistentes con el dashboard)."""
    opciones = dict(
        fg_color=colores["card"],
        corner_radius=16,
        border_width=1,
        border_color=colores["borde"],
    )
    opciones.update(kwargs)
    return ctk.CTkFrame(padre, **opciones)


def crear_encabezado(padre, colores, titulo, subtitulo):
    """Título + subtítulo estándar de cada pantalla interna."""
    contenedor = ctk.CTkFrame(padre, fg_color="transparent")

    ctk.CTkLabel(
        contenedor, text=titulo,
        font=("Segoe UI", 22, "bold"),
        text_color=colores["texto"]
    ).pack(anchor="w")

    ctk.CTkLabel(
        contenedor, text=subtitulo,
        font=("Segoe UI", 12),
        text_color=colores["subtext"]
    ).pack(anchor="w", pady=(2, 0))

    return contenedor


def crear_fila_tabla(padre, colores, celdas, ancho_columnas, acciones=None):
    """
    Fila de tabla estilo "card" (misma paleta que dash_fila). `celdas` es
    una lista de textos simples; para una celda con contenido custom
    (ej. avatar + nombre) pasa una función `fn(celda_frame)` en su lugar.
    `acciones` es una lista opcional de (texto, comando) mostrados a la
    derecha (ej. [("Editar", cb), ("Baja", cb)]).
    """
    fila = ctk.CTkFrame(padre, fg_color=colores["fila"], corner_radius=10, height=52)
    fila.pack(fill="x", pady=3, padx=2)
    fila.pack_propagate(False)

    for contenido, ancho in zip(celdas, ancho_columnas):
        celda = ctk.CTkFrame(fila, fg_color="transparent", width=ancho)
        celda.pack(side="left", fill="y", padx=(12, 0))
        celda.pack_propagate(False)

        if callable(contenido):
            contenido(celda)
        else:
            ctk.CTkLabel(
                celda, text=str(contenido), anchor="w",
                font=("Segoe UI", 12),
                text_color=colores["texto"]
            ).place(relx=0, rely=0.5, anchor="w")

    if acciones:
        for texto, comando in reversed(acciones):
            ctk.CTkButton(
                fila, text=texto, width=54, height=26,
                corner_radius=8, font=("Segoe UI", 11, "bold"),
                fg_color="transparent", text_color=colores["link"],
                hover_color=colores["card_inner"],
                command=comando
            ).pack(side="right", padx=(0, 6))

    return fila


def crear_encabezado_tabla(padre, colores, titulos, ancho_columnas):
    """Fila de encabezados (mayúsculas, gris) para una tabla tipo card."""
    fila = ctk.CTkFrame(padre, fg_color="transparent", height=28)
    fila.pack(fill="x", padx=2, pady=(0, 4))
    fila.pack_propagate(False)

    for titulo, ancho in zip(titulos, ancho_columnas):
        celda = ctk.CTkFrame(fila, fg_color="transparent", width=ancho)
        celda.pack(side="left", fill="y", padx=(12, 0))
        celda.pack_propagate(False)
        ctk.CTkLabel(
            celda, text=titulo.upper(), anchor="w",
            font=("Segoe UI", 10, "bold"),
            text_color=colores["subtext"]
        ).pack(anchor="w", expand=True)

    return fila
