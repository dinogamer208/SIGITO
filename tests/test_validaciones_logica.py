"""
Pruebas de la lógica de validación pura (sin base de datos):

- auth_controller.validar_password_nueva  → reglas de la contraseña nueva
- config_controller.correo_valido          → formato de dirección de correo

Correr desde la raíz del proyecto:  pytest
"""

from controllers import auth_controller
from controllers import config_controller


# ----------------------- contraseña nueva -----------------------

def test_password_valida_devuelve_none():
    assert auth_controller.validar_password_nueva("secreta1", "secreta1") is None


def test_password_vacia():
    assert auth_controller.validar_password_nueva("", "") is not None


def test_password_muy_corta():
    corta = "x" * (auth_controller.LONGITUD_MINIMA_PASSWORD - 1)
    assert auth_controller.validar_password_nueva(corta, corta) is not None


def test_password_confirmacion_no_coincide():
    assert auth_controller.validar_password_nueva("secreta1", "secreta2") is not None


# ----------------------- correo -----------------------

def test_correo_valido():
    assert config_controller.correo_valido("avisos@gmail.com") is True


def test_correo_con_subdominio():
    assert config_controller.correo_valido("admin@mail.institucion.edu") is True


def test_correo_vacio_invalido():
    assert config_controller.correo_valido("") is False


def test_correo_sin_arroba_invalido():
    assert config_controller.correo_valido("avisos.gmail.com") is False


def test_correo_sin_dominio_invalido():
    assert config_controller.correo_valido("avisos@") is False
