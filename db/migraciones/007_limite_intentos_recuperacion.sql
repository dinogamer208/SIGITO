-- =========================================================
-- db/migraciones/007_limite_intentos_recuperacion.sql
-- Límite de intentos para la recuperación de contraseña (código local
-- o por correo): máximo 5 intentos fallidos, después se bloquea por
-- 15 minutos (no permanente, para no dejar a un admin sin forma de
-- entrar si se equivoca varias veces con su propio código).
--
-- Aplicar después de 006_recuperacion_cuenta.sql.
-- =========================================================

USE sigito_db;

ALTER TABLE usuarios
    ADD COLUMN recovery_intentos_fallidos INT NOT NULL DEFAULT 0,
    ADD COLUMN recovery_bloqueado_hasta DATETIME NULL;

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('007_limite_intentos_recuperacion.sql');
