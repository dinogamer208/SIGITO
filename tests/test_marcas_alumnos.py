"""
Pruebas de las marcas de alumno (sin base de datos):

- asignacion_controller.clave_alumno      → mismo alumno aunque cambien
                                             mayúsculas, acentos o espacios
- asignacion_controller.historial_alumnos → conteo de daños/tardanzas y
                                             marca (No cuida / Tardista / ambas)
- asignacion_controller.alumnos_marcados  → solo marcados, en orden

La consulta a MySQL se reemplaza por filas falsas.

Correr desde la raíz del proyecto:  pytest
"""

import pytest

from controllers import asignacion_controller as ac


def _prestamo(nombre, danado=False, tarde=False, seccion="10-A", anio="2026",
              correo="alumno@estudiante.edu", telefono="7777-0000"):
    return {"nombre_completo": nombre, "seccion": seccion, "anio": anio,
            "telefono": telefono, "correo": correo,
            "devuelto_danado": int(danado), "tarde": int(tarde)}


class _CursorFalso:
    def __init__(self, filas):
        self._filas = filas

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return self._filas

    def close(self):
        pass


class _ConexionFalsa:
    def __init__(self, filas):
        self._filas = filas

    def cursor(self, dictionary=False):
        return _CursorFalso(self._filas)

    def close(self):
        pass


@pytest.fixture
def prestamos(monkeypatch):
    """Devuelve una función para fijar las filas que "trae" la BD."""
    def _fijar(filas):
        monkeypatch.setattr(ac, "obtener_conexion", lambda: _ConexionFalsa(filas))
    return _fijar


# ----------------------- identificar al alumno -----------------------

def test_clave_alumno_ignora_mayusculas_acentos_y_espacios():
    assert ac.clave_alumno("  María  José TORRES ") == ac.clave_alumno("maria jose torres")


def test_clave_alumno_distingue_nombres_distintos():
    assert ac.clave_alumno("María Torres") != ac.clave_alumno("María José Torres")


# ----------------------- marcas -----------------------

def test_sin_incidencias_no_tiene_marca(prestamos):
    prestamos([_prestamo("Ana")] * 5)
    assert ac.historial_alumno("Ana")["marca"] is None


def test_danos_uno_menos_del_limite_no_marca(prestamos):
    prestamos([_prestamo("Ana", danado=True)] * (ac.DANOS_PARA_NO_CUIDA - 1))
    assert ac.historial_alumno("Ana")["marca"] is None


def test_danos_en_el_limite_marca_no_cuida(prestamos):
    prestamos([_prestamo("Ana", danado=True)] * ac.DANOS_PARA_NO_CUIDA)
    historial = ac.historial_alumno("Ana")
    assert historial["danos"] == ac.DANOS_PARA_NO_CUIDA
    assert historial["marca"] == ac.MARCA_NO_CUIDA


def test_tardanzas_uno_menos_del_limite_no_marca(prestamos):
    prestamos([_prestamo("Ana", tarde=True)] * (ac.TARDANZAS_PARA_TARDISTA - 1))
    assert ac.historial_alumno("Ana")["marca"] is None


def test_tardanzas_en_el_limite_marca_tardista(prestamos):
    prestamos([_prestamo("Ana", tarde=True)] * ac.TARDANZAS_PARA_TARDISTA)
    historial = ac.historial_alumno("Ana")
    assert historial["tardanzas"] == ac.TARDANZAS_PARA_TARDISTA
    assert historial["marca"] == ac.MARCA_TARDISTA


def test_ambos_limites_marca_ambas(prestamos):
    prestamos(
        [_prestamo("Ana", danado=True)] * ac.DANOS_PARA_NO_CUIDA
        + [_prestamo("Ana", tarde=True)] * ac.TARDANZAS_PARA_TARDISTA
    )
    assert ac.historial_alumno("Ana")["marca"] == ac.MARCA_AMBAS


def test_un_prestamo_danado_y_tarde_cuenta_para_las_dos(prestamos):
    n = max(ac.DANOS_PARA_NO_CUIDA, ac.TARDANZAS_PARA_TARDISTA)
    prestamos([_prestamo("Ana", danado=True, tarde=True)] * n)
    assert ac.historial_alumno("Ana")["marca"] == ac.MARCA_AMBAS


def test_nombre_escrito_distinto_suma_al_mismo_alumno(prestamos):
    prestamos([
        _prestamo("María José Torres", danado=True),
        _prestamo("maria jose torres", danado=True),
        _prestamo("MARÍA  JOSÉ TORRES", danado=True),
    ])
    assert ac.historial_alumno("María José Torres")["marca"] == ac.MARCA_NO_CUIDA


def test_seccion_y_correo_son_los_del_prestamo_mas_reciente(prestamos):
    # La consulta real viene ordenada por hora_salida ASC: la última fila es la más reciente.
    prestamos([
        _prestamo("Ana", seccion="9-A", correo="viejo@x.edu"),
        _prestamo("Ana", seccion="10-B", correo="nuevo@x.edu"),
    ])
    historial = ac.historial_alumno("Ana")
    assert (historial["seccion"], historial["correo"]) == ("10-B", "nuevo@x.edu")


def test_alumno_sin_prestamos(prestamos):
    prestamos([])
    assert ac.historial_alumno("Nadie")["marca"] is None


# ----------------------- listado para reportes -----------------------

def test_alumnos_marcados_solo_incluye_marcados_y_en_orden(prestamos):
    prestamos(
        [_prestamo("Tardista", tarde=True)] * ac.TARDANZAS_PARA_TARDISTA
        + [_prestamo("Descuidado", danado=True)] * ac.DANOS_PARA_NO_CUIDA
        + [_prestamo("Ambas", danado=True, tarde=True)]
          * max(ac.DANOS_PARA_NO_CUIDA, ac.TARDANZAS_PARA_TARDISTA)
        + [_prestamo("Cumplido")] * 20
    )
    nombres = [a["nombre"] for a in ac.alumnos_marcados()]
    assert nombres == ["Ambas", "Descuidado", "Tardista"]


# ----------------------- buscador de alumnos (nuevo préstamo) -----------------------

def test_buscar_alumnos_por_parte_del_nombre_sin_acentos(prestamos):
    prestamos([_prestamo("María José Torres"), _prestamo("Luis Gómez"), _prestamo("José Pérez")])
    assert [a["nombre"] for a in ac.buscar_alumnos("jose")] == ["José Pérez", "María José Torres"]


def test_buscar_alumnos_trae_los_datos_mas_recientes(prestamos):
    prestamos([
        _prestamo("Ana Ruiz", seccion="9-A", telefono="1111", correo="viejo@x.edu"),
        _prestamo("ana ruiz", seccion="10-A", telefono="2222", correo="nuevo@x.edu"),
    ])
    (alumno,) = ac.buscar_alumnos("ana")
    assert (alumno["nombre"], alumno["seccion"], alumno["telefono"], alumno["correo"]) == \
        ("ana ruiz", "10-A", "2222", "nuevo@x.edu")


def test_buscar_alumnos_texto_vacio_no_devuelve_nada(prestamos):
    prestamos([_prestamo("Ana")])
    assert ac.buscar_alumnos("   ") == []
