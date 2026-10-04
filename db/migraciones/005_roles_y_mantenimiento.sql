-- =========================================================
-- db/migraciones/005_roles_y_mantenimiento.sql
-- 1. Agrega el rol 'limitado' a `usuarios` (acceso restringido: solo
--    código de barras/baja en Inventario, sin exportar en Reportes,
--    sin Historial ni Usuarios, y solo puede cambiar su contraseña
--    con autorización de un admin).
-- 2. Agrega a `mantenimientos` los campos que pide el formulario
--    "Enviar a mantenimiento" (solo admin, en Asignaciones): a dónde
--    se envió, fecha estipulada de devolución, y si ya regresó.
--
-- Aplicar después de 004_stock.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE usuarios
    MODIFY rol ENUM('admin', 'limitado') DEFAULT 'admin';

ALTER TABLE mantenimientos
    ADD COLUMN destino VARCHAR(150) NULL AFTER descripcion,
    ADD COLUMN fecha_retorno_estimada DATE NULL AFTER destino,
    ADD COLUMN estado ENUM('en_mantenimiento', 'regresado') DEFAULT 'en_mantenimiento' AFTER fecha_retorno_estimada;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('005_roles_y_mantenimiento.sql');
