-- QUICK ORDER - Esquema Inicial de Base de Datos (Módulo Productos)
-- Incremento 1: Catálogo de Productos

CREATE TABLE IF NOT EXISTS producto (
    producto_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
