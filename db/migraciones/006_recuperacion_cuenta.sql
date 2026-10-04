-- =========================================================
-- db/migraciones/006_recuperacion_cuenta.sql
-- Recuperación de cuenta local, sin depender de tocar el código:
-- 1. `correo` en usuarios: opcional, para el método de recuperación
--    por correo (además del ya existente `correo_copia_admin` que es
--    para avisos de atraso, no para login).
-- 2. `recovery_code_hash`: código de recuperación permanente que el
--    admin genera desde Configuración (bcrypt, igual que el password).
-- 3. `recovery_email_code_hash` / `_expira`: código temporal de un
--    solo uso enviado por correo cuando se pide "recuperar por correo".
--
-- Aplicar después de 005_roles_y_mantenimiento.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE usuarios
    ADD COLUMN correo VARCHAR(150) NULL AFTER usuario,
    ADD COLUMN recovery_code_hash VARCHAR(255) NULL,
    ADD COLUMN recovery_email_code_hash VARCHAR(255) NULL,
    ADD COLUMN recovery_email_code_expira DATETIME NULL;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('006_recuperacion_cuenta.sql');
