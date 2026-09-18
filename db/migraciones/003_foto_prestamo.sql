-- =========================================================
-- db/migraciones/003_foto_prestamo.sql
-- Agrega la columna `foto_alumno` a `asignaciones`: ruta de la foto
-- tomada con la cámara al registrar el préstamo (evidencia de quién
-- se llevó el equipo). Opcional: puede quedar NULL si no se tomó foto.
--
-- Aplicar después de 002_configuracion.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE asignaciones
    ADD COLUMN foto_alumno VARCHAR(255) NULL AFTER correo;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('003_foto_prestamo.sql');
