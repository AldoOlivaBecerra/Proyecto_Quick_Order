-- QUICK ORDER - Esquema de Base de Datos
-- Módulo 1: Catálogo de Productos
CREATE TABLE IF NOT EXISTS producto (
    producto_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

-- Módulo 2: Gestión de Comandas
CREATE TABLE IF NOT EXISTS comanda (
    comanda_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_hora_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en preparación', 'finalizada', 'cancelada'))
);

CREATE TABLE IF NOT EXISTS detalle_comanda (
    detalle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    especificaciones TEXT,
    FOREIGN KEY (comanda_id) REFERENCES comanda (comanda_id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES producto (producto_id)
);
