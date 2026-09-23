"""
utils/respaldo.py — Respaldo automático periódico.

Si está activado desde Configuración, cada N horas genera en la carpeta
backups/ dos archivos, y borra los más viejos de cada tipo para no
acumular espacio indefinidamente:

- inventario_*.zip: el inventario y sus fotos (mismo formato que
  "Descargar con fotos" en Configuración), para importarlo en otra PC.
- sigito_completo_*.zip: la base de datos COMPLETA (préstamos,
  devoluciones, daños, historial, usuarios, configuración...) como un
  script .sql, más todas las fotos. Es el que sirve para recuperar todo
  si la base de datos se daña (ver LEEME.txt dentro del zip).

iniciar()/detener() se llaman desde main.py al entrar y salir del
Dashboard (login/logout/cierre de la app), igual que utils/monitor.py.
"""

import glob
import os
import threading
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal

from controllers import config_controller, inventario_controller
from db.conexion import obtener_conexion
from utils.exportador import exportar_inventario_zip

CARPETA_RESPALDOS = "backups"
MAXIMO_RESPALDOS = 10
INTERVALO_REVISION_INACTIVO = 5 * 60  # revisa cada 5 min si se activó desde Configuración

# Carpetas de fotos que se incluyen en el respaldo completo.
CARPETAS_FOTOS = [
    os.path.join("assets", "fotos_articulos"),
    os.path.join("assets", "fotos_prestamos"),
    os.path.join("assets", "fotos_devoluciones"),
    os.path.join("assets", "etiquetas"),
]

_detener = threading.Event()
_hilo = None


def _borrar_viejos(patron):
    respaldos = sorted(glob.glob(os.path.join(CARPETA_RESPALDOS, patron)))
    for viejo in respaldos[:-MAXIMO_RESPALDOS]:
        try:
            os.remove(viejo)
        except OSError:
            pass


def _generar_respaldo():
    generar_respaldo_completo()

    datos = inventario_controller.datos_para_exportar(incluir_foto_path=True)
    if not datos:
        return

    os.makedirs(CARPETA_RESPALDOS, exist_ok=True)
    nombre = f"inventario_{datetime.now():%Y%m%d_%H%M%S}.zip"
    exportar_inventario_zip(datos, os.path.join(CARPETA_RESPALDOS, nombre))
    _borrar_viejos("inventario_*.zip")


# ------------------------------------------------------------
# Respaldo completo (base de datos + fotos)
# ------------------------------------------------------------

def _valor_sql(valor):
    """Convierte un valor de Python a literal SQL de MySQL."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float, Decimal)):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return f"X'{bytes(valor).hex()}'" if valor else "''"
    if isinstance(valor, datetime):
        return f"'{valor:%Y-%m-%d %H:%M:%S}'"
    if isinstance(valor, date):
        return f"'{valor:%Y-%m-%d}'"
    if isinstance(valor, timedelta):  # columnas TIME
        segundos = int(valor.total_seconds())
        return f"'{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}'"
    texto = str(valor)
    for original, escapado in (("\\", "\\\\"), ("'", "\\'"), ("\n", "\\n"),
                               ("\r", "\\r"), ("\x00", "\\0"), ("\x1a", "\\Z")):
        texto = texto.replace(original, escapado)
    return f"'{texto}'"


def volcar_base_de_datos() -> str:
    """
    Script .sql que recrea la base de datos completa: estructura de cada
    tabla (DROP + CREATE) y todos sus datos. Equivalente a mysqldump,
    pero sin depender de que mysqldump esté instalado.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT DATABASE()")
        (base,) = cursor.fetchone()
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tablas = [fila[0] for fila in cursor.fetchall()]

        lineas = [
            f"-- Respaldo completo de SIGITO ({base}) — {datetime.now():%Y-%m-%d %H:%M:%S}",
            "-- Restaurar: ver LEEME.txt",
            "",
            "SET NAMES utf8mb4;",
            "SET FOREIGN_KEY_CHECKS = 0;",
            f"CREATE DATABASE IF NOT EXISTS `{base}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            f"USE `{base}`;",
            "",
        ]
        for tabla in tablas:
            cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
            crear = cursor.fetchone()[1]
            lineas += [f"DROP TABLE IF EXISTS `{tabla}`;", f"{crear};"]

            cursor.execute(f"SELECT * FROM `{tabla}`")
            columnas = ", ".join(f"`{c}`" for c in cursor.column_names)
            filas = cursor.fetchall()
            # INSERT de varias filas a la vez (de 200 en 200), cada uno en
            # una sola línea: los saltos de línea de los textos van escapados.
            for i in range(0, len(filas), 200):
                valores = ",".join(
                    "(" + ",".join(_valor_sql(v) for v in fila) + ")" for fila in filas[i:i + 200]
                )
                lineas.append(f"INSERT INTO `{tabla}` ({columnas}) VALUES {valores};")
            lineas.append("")

        lineas.append("SET FOREIGN_KEY_CHECKS = 1;")
        return "\n".join(lineas) + "\n"
    finally:
        cursor.close()
        conexion.close()


_LEEME = """RESPALDO COMPLETO DE SIGITO
===========================

Contiene:
  - sigito_db.sql : toda la base de datos (inventario, préstamos,
                    devoluciones, daños, historial, usuarios, configuración).
  - assets/       : fotos de artículos, préstamos y daños, y etiquetas.

Para restaurar (REEMPLAZA los datos actuales por los de este respaldo):
  1. Cierra SIGITO.
  2. Descomprime este .zip.
  3. En una terminal, dentro de la carpeta descomprimida:
       mysql -u root -p --default-character-set=utf8mb4 < sigito_db.sql
  4. Copia la carpeta assets/ encima de la carpeta assets/ de SIGITO.
"""


def generar_respaldo_completo() -> str:
    """Genera backups/sigito_completo_<fecha>.zip y devuelve su ruta."""
    os.makedirs(CARPETA_RESPALDOS, exist_ok=True)
    ruta = os.path.join(CARPETA_RESPALDOS, f"sigito_completo_{datetime.now():%Y%m%d_%H%M%S}.zip")
    ruta_temporal = ruta + ".tmp"

    try:
        with zipfile.ZipFile(ruta_temporal, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sigito_db.sql", volcar_base_de_datos())
            zf.writestr("LEEME.txt", _LEEME)
            for carpeta in CARPETAS_FOTOS:
                for archivo in glob.glob(os.path.join(carpeta, "*")):
                    if os.path.isfile(archivo):
                        zf.write(archivo, archivo.replace(os.sep, "/"))
        # Se escribe a un .tmp y se renombra al final: si algo falla a la
        # mitad no queda un respaldo incompleto con apariencia de bueno.
        os.replace(ruta_temporal, ruta)
    finally:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

    _borrar_viejos("sigito_completo_*.zip")
    return ruta


def ultimo_respaldo_completo():
    """(ruta, fecha) del respaldo completo más reciente, o None."""
    respaldos = sorted(glob.glob(os.path.join(CARPETA_RESPALDOS, "sigito_completo_*.zip")))
    if not respaldos:
        return None
    return respaldos[-1], datetime.fromtimestamp(os.path.getmtime(respaldos[-1]))


def _ciclo():
    while not _detener.is_set():
        try:
            ajuste = config_controller.obtener_ajuste_respaldo()
        except Exception:
            ajuste = None

        if not ajuste or not ajuste["activo"]:
            _detener.wait(INTERVALO_REVISION_INACTIVO)
            continue

        try:
            _generar_respaldo()
        except Exception:
            pass  # un fallo puntual (ej. sin conexión) no debe tumbar el respaldo
        _detener.wait(ajuste["intervalo_horas"] * 3600)


def iniciar():
    """Arranca el hilo de respaldo si no está ya corriendo (llamar una
    vez por sesión; no hace nada si `activo` sigue en falso — el hilo
    solo queda revisando el ajuste cada 5 min)."""
    global _hilo
    if _hilo is not None and _hilo.is_alive():
        return
    _detener.clear()
    _hilo = threading.Thread(target=_ciclo, daemon=True)
    _hilo.start()


def detener():
    """Señala al hilo que pare; no bloquea esperándolo (es daemon)."""
    _detener.set()
