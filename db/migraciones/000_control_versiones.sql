-- =========================================================
-- db/migraciones/000_control_versiones.sql
-- Tabla de control: registra qué migraciones ya se aplicaron
-- en CADA base de datos local (la tuya, la de tus compañeros,
-- y en el futuro, la del servidor).
--
-- Ejecutar este archivo UNA SOLA VEZ, justo después de schema.sql,
-- en cualquier base de datos nueva.
-- =========================================================

USE sigito_db;

CREATE TABLE IF NOT EXISTS control_versiones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_migracion VARCHAR(150) NOT NULL UNIQUE,
    aplicada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Registra que la migración inicial (todo lo que ya está en schema.sql)
-- ya fue aplicada, para no reaplicarla por error.
INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('001_esquema_inicial.sql');