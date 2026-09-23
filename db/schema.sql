-- =========================================================
-- db/schema.sql
-- Base de datos del sistema SIGITO (versión LOCAL, sin servidor remoto)
-- =========================================================

CREATE DATABASE IF NOT EXISTS sigito_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE sigito_db;

-- ---------------------------------------------------------
-- Tabla: control_versiones (ver db/migraciones/000_control_versiones.sql)
-- ---------------------------------------------------------
CREATE TABLE control_versiones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_migracion VARCHAR(150) NOT NULL UNIQUE,
    aplicada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------
-- Tabla: categorias
-- ---------------------------------------------------------
CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255)
);

-- ---------------------------------------------------------
-- Tabla: articulos
-- ---------------------------------------------------------
CREATE TABLE articulos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_inventario VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    categoria_id INT NOT NULL,
    marca VARCHAR(100),
    modelo VARCHAR(100),
    serie VARCHAR(100),
    foto_path VARCHAR(255),
    estado_fisico ENUM('bueno', 'regular', 'dañado') DEFAULT 'bueno',
    estado_disponibilidad ENUM('disponible', 'de_baja') DEFAULT 'disponible',
    cantidad_total INT NOT NULL DEFAULT 1,
    cantidad_disponible INT NOT NULL DEFAULT 1,
    fecha_adquisicion DATE,
    ubicacion_actual VARCHAR(150),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

-- ---------------------------------------------------------
-- Tabla: usuarios (login del sistema, admin)
-- ---------------------------------------------------------
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    correo VARCHAR(150) NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'limitado') DEFAULT 'admin',
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recovery_code_hash VARCHAR(255) NULL,
    recovery_email_code_hash VARCHAR(255) NULL,
    recovery_email_code_expira DATETIME NULL,
    recovery_intentos_fallidos INT NOT NULL DEFAULT 0,
    recovery_bloqueado_hasta DATETIME NULL
);

-- ---------------------------------------------------------
-- Tabla: profesores_autorizados (catálogo, sin login propio)
-- ---------------------------------------------------------
CREATE TABLE profesores_autorizados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    activo BOOLEAN DEFAULT TRUE
);

-- ---------------------------------------------------------
-- Tabla: asignaciones (préstamos y devoluciones)
-- ---------------------------------------------------------
CREATE TABLE asignaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    articulo_id INT NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    nombre_completo VARCHAR(150) NOT NULL,
    seccion VARCHAR(20) NOT NULL,
    anio VARCHAR(20) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    foto_alumno VARCHAR(255) NULL,
    profesor_autoriza_id INT NOT NULL,
    hora_salida DATETIME NOT NULL,
    hora_estimada_devolucion DATETIME NOT NULL,
    hora_entrada_real DATETIME NULL,
    estado ENUM('en_uso', 'devuelto', 'atrasado') DEFAULT 'en_uso',
    correo_aviso_enviado BOOLEAN DEFAULT FALSE,
    usuario_registro_id INT NOT NULL,
    usuario_devolucion_id INT NULL,
    devuelto_danado BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones_devolucion TEXT NULL,
    foto_devolucion VARCHAR(255) NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (articulo_id) REFERENCES articulos(id),
    FOREIGN KEY (profesor_autoriza_id) REFERENCES profesores_autorizados(id),
    FOREIGN KEY (usuario_registro_id) REFERENCES usuarios(id),
    FOREIGN KEY (usuario_devolucion_id) REFERENCES usuarios(id)
);

-- ---------------------------------------------------------
-- Tabla: historial_movimientos (auditoría)
-- ---------------------------------------------------------
CREATE TABLE historial_movimientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    articulo_id INT NOT NULL,
    asignacion_id INT NULL,
    tipo_movimiento ENUM('alta', 'prestamo', 'devolucion', 'baja', 'mantenimiento') NOT NULL,
    usuario_id INT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detalle TEXT,
    FOREIGN KEY (articulo_id) REFERENCES articulos(id),
    FOREIGN KEY (asignacion_id) REFERENCES asignaciones(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- ---------------------------------------------------------
-- Tabla: mantenimientos
-- ---------------------------------------------------------
CREATE TABLE mantenimientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    articulo_id INT NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT,
    destino VARCHAR(150),
    fecha_retorno_estimada DATE,
    estado ENUM('en_mantenimiento', 'regresado') DEFAULT 'en_mantenimiento',
    costo DECIMAL(10,2),
    tecnico VARCHAR(150),
    FOREIGN KEY (articulo_id) REFERENCES articulos(id)
);

-- ---------------------------------------------------------
-- Tabla: configuracion (ajustes editables desde la app)
-- Ver db/migraciones/002_configuracion.sql. La contraseña de
-- aplicación SMTP se guarda cifrada con Fernet (utils/seguridad.py).
-- ---------------------------------------------------------
CREATE TABLE configuracion (
    clave          VARCHAR(60) PRIMARY KEY,
    valor          TEXT,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO configuracion (clave, valor) VALUES
    ('correo_remitente',   ''),
    ('smtp_app_password',   ''),
    ('correo_copia_admin',  '');

-- ---------------------------------------------------------
-- Usuario admin por defecto: usuario "admin", contraseña "admin123"
-- (hash bcrypt, costo 10 — ver utils/seguridad.py). Cámbiala desde
-- Configuración > Contraseña de acceso en el primer inicio de sesión.
-- ---------------------------------------------------------
INSERT INTO usuarios (nombre, usuario, password_hash, rol, activo) VALUES
    ('Administrador', 'admin', '$2b$10$ATNOGXNgpYKT602UVXacvO9R7RkboSoH5IaWaxVENvwgC2q1y0uVm', 'admin', TRUE);

-- Registra las migraciones ya incorporadas a este schema, para que
-- nadie las vuelva a aplicar por error.
INSERT INTO control_versiones (nombre_migracion) VALUES
    ('001_esquema_inicial.sql'),
    ('002_configuracion.sql'),
    ('003_foto_prestamo.sql'),
    ('004_stock.sql'),
    ('005_roles_y_mantenimiento.sql'),
    ('006_recuperacion_cuenta.sql'),
    ('007_limite_intentos_recuperacion.sql'),
    ('008_devolucion_danada.sql'),
    ('009_foto_devolucion.sql'),
    ('010_corregir_enum_danado.sql');

-- =========================================================
-- NOTA: Ya no se crea un usuario de MySQL separado (sigito_app)
-- porque por ahora el sistema es 100% local, cada quien usa su
-- propio 'root' de MySQL en su computadora.
--
-- Si en el futuro se conecta a un servidor real en red, aquí se
-- agregaría de nuevo algo como:
--
-- CREATE USER 'sigito_app'@'%' IDENTIFIED BY 'CAMBIAR_ESTO';
-- GRANT SELECT, INSERT, UPDATE ON sigito_db.* TO 'sigito_app'@'%';
-- FLUSH PRIVILEGES;
-- =========================================================