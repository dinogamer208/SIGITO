-- =========================================================
-- db/migraciones/008_devolucion_danada.sql
-- Permite que el profesor registre, al recibir una devolución, que el
-- equipo regresó dañado y describa el daño:
--   * devuelto_danado: TRUE si el equipo llegó dañado.
--   * observaciones_devolucion: descripción del daño (opcional).
--
-- Aplicar después de 007_limite_intentos_recuperacion.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE asignaciones
    ADD COLUMN devuelto_danado BOOLEAN NOT NULL DEFAULT FALSE AFTER usuario_devolucion_id,
    ADD COLUMN observaciones_devolucion TEXT NULL AFTER devuelto_danado;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('008_devolucion_danada.sql');
