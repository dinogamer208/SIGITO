-- =========================================================
-- db/migraciones/009_foto_devolucion.sql
-- Agrega `foto_devolucion` a `asignaciones`: ruta de la foto del equipo
-- tomada con la cámara al registrar una devolución dañada (evidencia
-- del daño). Opcional: puede quedar NULL.
--
-- Aplicar después de 008_devolucion_danada.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE asignaciones
    ADD COLUMN foto_devolucion VARCHAR(255) NULL AFTER observaciones_devolucion;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('009_foto_devolucion.sql');
