"""
Pruebas del context manager db.conexion.transaccion.

El punto clave: una consulta que falla NO debe dejar la conexión colgada.
Con pool_size=3, si no se devolviera al pool, a la cuarta iteración la
app se quedaría esperando para siempre en get_connection().

Requiere un MySQL local accesible (se salta si no lo hay).
"""
import pytest

from db.conexion import hay_conexion_servidor, transaccion

pytestmark = pytest.mark.skipif(
    not hay_conexion_servidor(), reason="no hay MySQL local disponible"
)


def test_error_en_consulta_devuelve_la_conexion_al_pool():
    # Muchas más iteraciones que pool_size (3): si cada error filtrara la
    # conexión, esto se colgaría o lanzaría PoolError antes de terminar.
    for _ in range(15):
        with pytest.raises(Exception):
            with transaccion() as (cursor, _con):
                cursor.execute("SELECT * FROM tabla_inexistente_zzz")

    # El pool sigue perfectamente usable después de todos esos errores.
    with transaccion(dictionary=True) as (cursor, _con):
        cursor.execute("SELECT 1 AS ok")
        assert cursor.fetchone()["ok"] == 1


def test_transaccion_hace_rollback_si_el_bloque_lanza():
    nombre = "_ZZZ_categoria_de_prueba_rollback"
    try:
        with pytest.raises(RuntimeError):
            with transaccion() as (cursor, _con):
                cursor.execute(
                    "INSERT INTO categorias (nombre, descripcion) VALUES (%s, 'tmp')",
                    (nombre,),
                )
                raise RuntimeError("falla después del INSERT")

        with transaccion(dictionary=True) as (cursor, _con):
            cursor.execute(
                "SELECT COUNT(*) AS n FROM categorias WHERE nombre = %s", (nombre,)
            )
            assert cursor.fetchone()["n"] == 0, "el INSERT debió revertirse"
    finally:
        with transaccion() as (cursor, _con):
            cursor.execute("DELETE FROM categorias WHERE nombre = %s", (nombre,))
