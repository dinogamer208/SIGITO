-- =========================================================
-- db/migraciones/002_configuracion.sql
-- Agrega la tabla `configuracion`: pares clave/valor para los
-- ajustes que se editan desde la pantalla de Configuración de la
-- app (correo remitente de los avisos de atraso, contraseña de
-- aplicación SMTP, correo de copia al administrador).
--
-- La contraseña de aplicación SMTP se guarda CIFRADA con Fernet
-- (ver utils/seguridad.py). La llave vive fuera del repo, en
-- ~/.sigito/secret.key, y se genera sola la primera vez.
--
-- Autor: pantalla de Configuración (Persona 4 / Persona 5).
-- Aplicar después de 001_esquema_inicial.sql.
-- =========================================================

USE sigito_db;

CREATE TABLE IF NOT EXISTS configuracion (
    clave         VARCHAR(60) PRIMARY KEY,
    valor         TEXT,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   ON UPDATE CURRENT_TIMESTAMP
);

-- Filas por defecto (vacías): la app las rellena desde la pantalla
-- de Configuración. INSERT IGNORE para no pisar valores ya guardados.
INSERT IGNORE INTO configuracion (clave, valor) VALUES
    ('correo_remitente',   ''),
    ('smtp_app_password',   ''),   -- se guarda cifrada
    ('correo_copia_admin',  '');

INSERT IGNORE INTO control_versiones (nombre_migracion)
VALUES ('002_configuracion.sql');
