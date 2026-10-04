"""
utils/validaciones.py — Validación de formularios (compartido por todos).

Responsable: compartido — cada persona agrega las validaciones que
necesite su propio formulario, pero centralizadas aquí para reutilizar.

Qué debe hacer este archivo:
1. Funciones puras (sin Tkinter, sin BD) que reciban un valor y
   devuelvan True/False o lancen ValueError con mensaje claro.
2. Ejemplos típicos: correo_valido(), campo_no_vacio(), fecha_valida().

Esqueleto:
"""

import re

_REGEX_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def correo_valido(correo: str) -> bool:
    return bool(_REGEX_CORREO.match(correo or ""))


def campo_no_vacio(valor: str) -> bool:
    return bool(valor and valor.strip())


def fecha_valida(fecha_str: str, formato: str = "%Y-%m-%d") -> bool:
    from datetime import datetime
    try:
        datetime.strptime(fecha_str, formato)
        return True
    except ValueError:
        return False


def variantes_codigo_escaneado(codigo: str) -> list[str]:
    """
    Formas posibles de un código leído con el lector de barras, en orden
    de prioridad. Si el lector está configurado con teclado en inglés y
    Windows en español, algunos caracteres llegan cambiados (ej. "'009"
    en vez de "009", o "TEC'0007" en vez de "TEC-0007"), así que además
    del código tal cual se prueba sin el ' y con - en su lugar.
    """
    codigo = (codigo or "").strip()
    variantes = [codigo, codigo.replace("'", ""), codigo.replace("'", "-")]
    return [v for i, v in enumerate(variantes) if v and v not in variantes[:i]]
