"""
models/articulo.py — Modelo de datos Artículo (inventario).

Responsable: Persona 3.

Qué debe hacer este archivo:
1. Definir una clase Articulo que represente una fila de `articulos`,
   incluyendo código de barras, categoría y estado.
2. Igual que usuario.py: solo modelado del dato, sin queries aquí.

Esqueleto:
"""

from dataclasses import dataclass


@dataclass
class Articulo:
    def __init__(self, id, codigo_inventario, nombre, categoria_id,
                marca, modelo, serie, foto_path, estado_fisico,
                estado_disponibilidad, fecha_adquisicion,
                ubicacion_actual, uuid_local=None, fecha_creacion=None,
                **kwargs):
        self.id = id
        self.codigo_inventario = codigo_inventario
        self.nombre = nombre
        self.categoria_id = categoria_id
        self.marca = marca
        self.modelo = modelo
        self.serie = serie
        self.foto_path = foto_path
        self.estado_fisico = estado_fisico
        self.estado_disponibilidad = estado_disponibilidad
        self.fecha_adquisicion = fecha_adquisicion
        self.ubicacion_actual = ubicacion_actual
        self.uuid_local = uuid_local
        self.fecha_adquisicion = fecha_creacion

    def esta_disponible(self):
        return self.estado_disponibilidad == "disponible"
    
    def __repr__(self):
        return f"<Articulo {self.codigo_inventario} - {self.nombre}>"
    
    