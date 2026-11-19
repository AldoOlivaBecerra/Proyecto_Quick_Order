# QUICK ORDER - Sistema de Gestión de Comandas

Sistema para restaurantes de comida rápida desarrollado de forma modular e incremental con arquitectura en 3 capas (*Controlador -> Servicio -> Repositorio*).

---

## 📦 Incrementos Implementados

### 🟢 Incremento 1: Módulo de Productos (Catálogo)
- Consulta y visualización del catálogo de productos activos (`activo = 1`).
- Exclusión de productos inactivos (`activo = 0`).
- Interfaz responsiva con tarjetas y estado de catálogo vacío.
- Manejo controlado de fallos en SQLite con respuestas HTTP seguras.

### 🟢 Incremento 2: Módulo de Comandas (Gestión de Pedidos)
- **Registro de nuevas comandas**:
  - Selección dinámica de productos activos.
  - Validación de cantidades enteras positivas (`cantidad > 0`).
  - Especificaciones de texto libre opcionales por producto.
  - Adición y eliminación interactiva de productos antes del guardado.
  - Estado inicial obligatorio: `pendiente`.
- **Consulta de comandas**:
  - Listado general de comandas con identificador, fecha/hora, estado y resumen de unidades/ítems.
  - Pantalla de detalle individual con la lista desglosada de productos y especificaciones.
- **Modificación de comandas**:
  - Exclusivamente permitido en estado `pendiente`.
  - Permite modificar productos, cantidades y especificaciones conservando al menos un ítem.
  - Bloqueo estricto si la comanda está en preparación, finalizada o cancelada.
  - Actualización automática de `fecha_hora_actualizacion`.
- **Cancelación de comandas**:
  - Exclusivamente permitido en estado `pendiente`.
  - Cancelación lógica (cambio de estado a `cancelada`), conservando los registros e historial en SQLite.

### 🟢 Incremento 3: Módulo de Cocina (Kitchen Display System — KDS)
- **Monitor de Cocina KDS**:
  - Pantalla visual tipo tablero Kanban en `/cocina` para el personal de cocina.
  - Muestra únicamente comandas activas (`pendiente` y `en preparación`).
  - Exclusión automática de comandas canceladas y finalizadas.
  - Orden cronológico estricto de llegada (FIFO: First-In, First-Out).
  - Desglose visible de identificador `#ID`, productos, cantidades destacadas y especificaciones.
- **Transiciones de Estado Controladas**:
  - Iniciar preparación: `pendiente` &rarr; `en preparación`.
  - Finalizar preparación: `en preparación` &rarr; `finalizada` (retirándola del monitor activo).
  - Bloqueo estricto de saltos de estado directos o acciones sobre pedidos cancelados/finalizados.
- **Actualización Automática**:
  - Short Polling asíncrono cada 1.5 segundos mediante `GET /cocina/api/activas`.
  - Reflejo automático de pedidos creados en caja en menos de 3 segundos sin recargar la página.
  - Actualización reactiva del DOM sin parpadeos ni duplicidad de tarjetas.

### 🟢 Incremento 4: Módulo de Reportes (Productos Más Vendidos)
- **Reporte Analítico de Ventas**:
  - Pantalla visual e interactiva en `/reportes` y `/reportes/mas-vendidos`.
  - Cálculo acumulado de unidades vendidas por producto obtenido directamente de SQLite.
  - Filtrado estricto: contabiliza **exclusivamente comandas finalizadas**.
  - Exclusión absoluta de comandas `pendiente`, `en preparación` y `cancelada`.
  - Ordenamiento descendente de mayor a menor demanda (`total_vendido DESC`).
  - Desempate alfabético determinista por nombre de producto (`p.nombre ASC`).
  - Métricas clave (KPIs): Total de unidades despachadas, Producto estrella / más vendido y Variedad de productos con demanda.
  - Cálculo de porcentaje de participación de cada producto sobre el total general.
  - Manejo seguro de casos límite (cero ventas, estado vacío, historial de productos descontinuados).

---

## 🏗️ Arquitectura del Proyecto

El sistema aplica el patrón **Application Factory** y **Blueprints** de Flask en una arquitectura de 3 capas:

$$\text{Rutas / Vistas (routes.py)} \longleftrightarrow \text{Lógica de Negocio (service.py)} \longleftrightarrow \text{Acceso a Datos (repository.py)} \longleftrightarrow \text{SQLite (quick\_order.db)}$$

```text
Proyecto_Quick_Order/
│
├── app/
│   ├── __init__.py                # Fábrica de aplicaciones (create_app) y registro de Blueprints
│   ├── config.py                  # Configuraciones (Desarrollo, Pruebas con BD aislada)
│   ├── database.py                # Conexión, cierre y creación automática de SQLite
│   ├── schema.sql                 # Esquema DDL (producto, comanda, detalle_comanda)
│   ├── seed.py                    # Datos de prueba para el catálogo de productos
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── productos/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # Controlador de productos
│   │   │   ├── service.py         # Lógica de negocio del catálogo
│   │   │   └── repository.py      # Consultas SQL para productos
│   │   │
│   │   ├── comandas/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # Controlador de comandas (caja)
│   │   │   ├── service.py         # Lógica de negocio (estados, validaciones, transacciones)
│   │   │   └── repository.py      # Consultas SQL sobre comanda y detalle_comanda
│   │   │
│   │   ├── cocina/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # Controlador de cocina (vistas KDS y API polling)
│   │   │   ├── service.py         # Lógica de cocina (transiciones válidas, FIFO, validaciones)
│   │   │   └── repository.py      # Consultas SQL de órdenes activas y actualización de estados
│   │   │
│   │   └── reportes/
│   │       ├── __init__.py
│   │       ├── routes.py          # Controlador de reportes (vistas analíticas)
│   │       ├── service.py         # Lógica de cálculo, porcentajes y KPIs
│   │       └── repository.py      # Consultas analíticas SQL con agregación
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css         # Hoja de estilos global, fast-food POS, KDS y KPIs
│   │   └── js/
│   │       ├── main.js            # Comportamiento interactivo de formularios
│   │       └── cocina.js          # Polling cada 1.5s y actualización reactiva de cocina
│   │
│   └── templates/
│       ├── base.html              # Plantilla base con navegación y notificaciones flash
│       ├── productos/
│       │   └── catalogo.html      # Catálogo de productos
│       ├── comandas/
│       │   ├── lista.html         # Listado general de comandas en caja
│       │   ├── crear.html         # Formulario interactivo de nueva comanda
│       │   ├── detalle.html       # Vista de detalle completo de la comanda
│       │   └── editar.html        # Formulario de modificación de comanda pendiente
│       ├── cocina/
│       │   └── pantalla.html      # Tablero Kanban del monitor de cocina (KDS)
│       └── reportes/
│           └── mas_vendidos.html  # Pantalla de productos más vendidos y KPIs
│
├── data/                          # Almacén de base de datos SQLite
│   ├── .gitkeep
│   ├── quick_order.db             # Base de datos de desarrollo
│   └── quick_order_test.db        # Base de datos aislada para pruebas
│
├── tests/
│   ├── __init__.py
│   ├── test_productos.py          # 7 pruebas automatizadas de productos
│   ├── test_comandas.py           # 14 pruebas automatizadas de comandas
│   ├── test_cocina.py             # 12 pruebas automatizadas de cocina
│   └── test_reportes.py           # 11 pruebas automatizadas de reportes
│
├── requirements.txt               # Dependencias del proyecto (Flask)
├── run.py                         # Punto de entrada para ejecutar el servidor local
└── README.md                      # Documentación del sistema
```

---

## 🗄️ Esquema de Base de Datos SQLite

```sql
-- Tabla Producto
CREATE TABLE IF NOT EXISTS producto (
    producto_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

-- Tabla Comanda
CREATE TABLE IF NOT EXISTS comanda (
    comanda_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_hora_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'en preparación', 'finalizada', 'cancelada'))
);

-- Tabla DetalleComanda
CREATE TABLE IF NOT EXISTS detalle_comanda (
    detalle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    especificaciones TEXT,
    FOREIGN KEY (comanda_id) REFERENCES comanda (comanda_id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES producto (producto_id)
);
```

---

## 🚀 Guía de Instalación y Ejecución

### 1. Activar el entorno virtual

En la terminal de Visual Studio Code (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```powershell
python run.py
```

### 4. Abrir en el navegador

* Catálogo de productos: [http://127.0.0.1:5000/productos](http://127.0.0.1:5000/productos)
* Gestión de comandas (Caja): [http://127.0.0.1:5000/comandas](http://127.0.0.1:5000/comandas)
* Monitor de Cocina (KDS): [http://127.0.0.1:5000/cocina](http://127.0.0.1:5000/cocina)

---

## 🧪 Ejecución de Pruebas Automatizadas

Para ejecutar la suite completa de 32 pruebas automatizadas (7 de Productos + 14 de Comandas + 11 de Cocina):

```powershell
.\venv\Scripts\python -m unittest discover -s tests -v
```
