-- seed_data.sql — Datos de prueba iniciales.
-- Responsable: Persona 1 (con ayuda de Persona 6 para casos de prueba).
--
-- Ejecutar SOLO después de schema.sql. Sirve para probar login,
-- inventario y asignaciones sin capturar todo a mano.

USE sigito;

INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES
('Admin Prueba', 'admin@sigito.test', '$2b$12$REEMPLAZAR_CON_HASH_REAL', 'admin');
-- TODO: generar el hash real con utils/seguridad.py antes de insertar

INSERT INTO categorias (nombre) VALUES
('Proyectores'), ('Laptops'), ('Impresoras'), ('Otros');

-- TODO: Persona 6 agrega artículos y asignaciones de ejemplo aquí
