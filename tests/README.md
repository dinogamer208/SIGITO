# tests/ — Pruebas de la lógica importante de SIGITO

```bash
pip install -r requirements.txt   # incluye pytest
pytest                            # desde la raíz del proyecto
```

## Qué cubren

| Archivo | Qué prueba | ¿Necesita MySQL? |
|---|---|---|
| `test_seguridad.py` | Hash de contraseñas (bcrypt) y cifrado/descifrado de credenciales (Fernet). La llave Fernet se aísla en un archivo temporal. | No |
| `test_validaciones_logica.py` | Reglas de la contraseña nueva (`auth_controller.validar_password_nueva`) y formato de correo (`config_controller.correo_valido`). | No |
| `test_marcas_alumnos.py` | Marcas de alumno "No cuida" / "Tardista" / ambas (`asignacion_controller.historial_alumnos`, `alumnos_marcados`): límites, nombres escritos distinto y orden del reporte. La consulta a MySQL se reemplaza por filas falsas. | No |

Las pruebas que sí tocan la base de datos (login real, `cambiar_password`,
`obtener_config`, consultas de reportes) se ejecutan en vivo desde la
pantalla **Configuración → Diagnóstico del sistema** dentro de la app,
que corre `utils/diagnostico.ejecutar_diagnostico()`.

## Agregar una prueba nueva

Crea `tests/test_<lo_que_sea>.py` con funciones `test_*`. Manténlas sin
dependencia de MySQL cuando se pueda (validaciones, formato, cálculos);
si necesitan datos reales, va en el diagnóstico de la app.
