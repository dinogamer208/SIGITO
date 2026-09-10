"""
Pruebas de utils/seguridad.py — hash de contraseñas (bcrypt) y cifrado
de credenciales (Fernet). No tocan la base de datos.

Correr desde la raíz del proyecto:  pytest
"""

import pytest

from utils import seguridad


def test_hash_password_round_trip():
    h = seguridad.hash_password("MiClave123")
    assert h != "MiClave123"                       # no se guarda en claro
    assert seguridad.verificar_password("MiClave123", h) is True


def test_hash_password_rechaza_incorrecta():
    h = seguridad.hash_password("MiClave123")
    assert seguridad.verificar_password("otra-clave", h) is False


def test_hash_password_usa_sal_distinta_cada_vez():
    assert seguridad.hash_password("misma") != seguridad.hash_password("misma")


@pytest.fixture
def llave_temporal(tmp_path, monkeypatch):
    """Aísla la llave Fernet en un archivo temporal para no tocar ~/.sigito."""
    monkeypatch.setenv("SIGITO_SECRET_KEY", str(tmp_path / "secret.key"))
    yield


def test_cifrar_descifrar_round_trip(llave_temporal):
    token = seguridad.cifrar("app-password-de-gmail")
    assert token != "app-password-de-gmail"
    assert seguridad.descifrar(token) == "app-password-de-gmail"


def test_cifrar_vacio_devuelve_vacio(llave_temporal):
    assert seguridad.cifrar("") == ""
    assert seguridad.descifrar("") == ""


def test_llave_se_genera_una_sola_vez(llave_temporal):
    primera = seguridad.cargar_llave()
    segunda = seguridad.cargar_llave()
    assert primera == segunda
