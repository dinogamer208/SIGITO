-- =========================================================
-- db/migraciones/004_stock.sql
-- Reemplaza el control de disponibilidad por artículo individual
-- ("disponible"/"prestado" por fila) por un control de stock: cada
-- fila de `articulos` representa un tipo de artículo con una cantidad
-- total y una cantidad disponible, en vez de tener que dar de alta una
-- fila por cada unidad física (lo que generaba códigos duplicados con
-- sufijo -2/-3... y volvía lenta/trabada la pantalla al agregar o
-- prestar varias unidades de golpe, por crear muchas filas una por una).
--
-- Aplicar después de 003_foto_prestamo.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE articulos
    ADD COLUMN cantidad_total INT NOT NULL DEFAULT 1 AFTER estado_disponibilidad,
    ADD COLUMN cantidad_disponible INT NOT NULL DEFAULT 1 AFTER cantidad_total;

-- Los artículos que estaban marcados "prestado" (viejo modelo por fila)
-- pasan a cantidad_disponible = 0 antes de quitar ese valor del ENUM.
UPDATE articulos SET cantidad_disponible = 0 WHERE estado_disponibilidad = 'prestado';
UPDATE articulos SET estado_disponibilidad = 'disponible' WHERE estado_disponibilidad = 'prestado';

ALTER TABLE articulos
    MODIFY estado_disponibilidad ENUM('disponible', 'de_baja') DEFAULT 'disponible';

ALTER TABLE asignaciones
    ADD COLUMN cantidad INT NOT NULL DEFAULT 1 AFTER articulo_id;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('004_stock.sql');
