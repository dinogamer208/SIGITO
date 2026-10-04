-- =========================================================
-- db/migraciones/010_corregir_enum_danado.sql
-- Corrige el valor 'dañado' del ENUM articulos.estado_fisico en bases
-- creadas con instalar.ps1 antes del arreglo de codificación: el
-- schema se pasaba a mysql por una tubería de PowerShell que rompía la
-- "ñ" (quedaba 'da├▒ado'), y al marcar un artículo como dañado MySQL
-- respondía "Data truncated for column 'estado_fisico'".
--
-- Correr con: mysql --default-character-set=utf8mb4 ... < este_archivo
-- Aplicar después de 009_foto_devolucion.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE articulos
    MODIFY estado_fisico ENUM('bueno', 'regular', 'dañado') DEFAULT 'bueno';

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('010_corregir_enum_danado.sql');
