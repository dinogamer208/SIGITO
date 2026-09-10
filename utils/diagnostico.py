"""
utils/diagnostico.py — Autochequeo de la lógica importante del sistema.

Lo usa la pantalla de Configuración (botón "Ejecutar diagnóstico") para
verificar de un vistazo que las piezas críticas responden: conexión a la
base de datos, hash de contraseñas, cifrado de credenciales y las
consultas que alimentan el dashboard y los avisos de atraso.

Cada chequeo devuelve un dict {nombre, ok, detalle}. `ejecutar_diagnostico()`
nunca lanza: atrapa cualquier excepción y la reporta como ok=False.
"""

import time


def _chequeo(nombre, fn):
    inicio = time.perf_counter()
    try:
        detalle = fn() or "OK"
        ok = True
    except Exception as error:  # noqa: BLE001 - queremos reportar cualquier fallo
        detalle = f"{type(error).__name__}: {error}"
        ok = False
    ms = (time.perf_counter() - inicio) * 1000
    return {"nombre": nombre, "ok": ok, "detalle": detalle, "ms": round(ms)}


def _check_conexion_bd():
    from db.conexion import obtener_conexion

    conexion = obtener_conexion()
    conexion.close()
    return "Conexión abierta y devuelta al pool"


def _check_hash_password():
    from utils.seguridad import hash_password, verificar_password

    h = hash_password("clave-de-prueba")
    if not verificar_password("clave-de-prueba", h):
        raise AssertionError("verificar_password devolvió False para la contraseña correcta")
    if verificar_password("otra-clave", h):
        raise AssertionError("verificar_password devolvió True para una contraseña incorrecta")
    return "hash + verificación correctos"


def _check_cifrado_fernet():
    from utils.seguridad import cifrar, descifrar

    original = "app-password-123"
    token = cifrar(original)
    if token == original:
        raise AssertionError("El texto no quedó cifrado")
    if descifrar(token) != original:
        raise AssertionError("El descifrado no devolvió el texto original")
    return "cifrado + descifrado correctos"


def _check_resumen_estados():
    from controllers import reportes_controller

    filas = reportes_controller.resumen_articulos_por_estado()
    total = sum(f["cantidad"] for f in filas)
    return f"{len(filas)} estados, {total} artículos"


def _check_prestamos_vencidos():
    from controllers import reportes_controller

    filas = reportes_controller.prestamos_vencidos()
    return f"{len(filas)} préstamo(s) vencido(s)"


def _check_listar_articulos():
    from controllers import inventario_controller

    filas = inventario_controller.listar_articulos()
    return f"{len(filas)} artículo(s) en inventario"


def _check_config_correo():
    from controllers import config_controller

    cfg = config_controller.obtener_config()
    faltan = [
        etiqueta
        for etiqueta, clave in (("remitente", "correo_remitente"),
                                ("contraseña de aplicación", "smtp_app_password"))
        if not cfg.get(clave)
    ]
    if faltan:
        raise AssertionError("Falta configurar: " + ", ".join(faltan))
    return f"remitente {cfg['correo_remitente']} configurado"


_CHEQUEOS = (
    ("Conexión a la base de datos", _check_conexion_bd),
    ("Hash de contraseñas (bcrypt)", _check_hash_password),
    ("Cifrado de credenciales (Fernet)", _check_cifrado_fernet),
    ("Resumen de inventario por estado", _check_resumen_estados),
    ("Consulta de préstamos vencidos", _check_prestamos_vencidos),
    ("Listado de artículos", _check_listar_articulos),
    ("Configuración de correo de avisos", _check_config_correo),
)


def ejecutar_diagnostico() -> list[dict]:
    """Corre todos los chequeos en orden y devuelve la lista de resultados."""
    return [_chequeo(nombre, fn) for nombre, fn in _CHEQUEOS]
