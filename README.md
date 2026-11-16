# QUICK ORDER - Sistema de Gestión de Comandas

Sistema para restaurantes de comida rápida desarrollado de forma modular e incremental con arquitectura en 3 capas (*Controlador -> Servicio -> Repositorio*).

---

## 📦 Incremento 1: Módulo de Productos (Consulta)

En este primer incremento se implementó la arquitectura base completa y la **consulta / visualización del catálogo de productos activos** almacenados en SQLite.

### Características implementadas:
1. **Catálogo de productos activos**: Muestra únicamente los productos con estado `activo = 1`.
2. **Exclusión de inactivos**: Los productos marcados como `activo = 0` no se presentan al cliente.
3. **Manejo de estado vacío**: Presenta una interfaz amigable cuando no hay productos disponibles.
4. **Resiliencia ante fallos**: Manejo controlado de excepciones de base de datos con respuesta HTTP 500 y alerta visual.
5. **Autocreación de base de datos**: Si el archivo SQLite no existe, el sistema lo crea automáticamente aplicando `schema.sql` y sembrando datos de prueba iniciales.
6. **Separación de responsabilidades en 3 capas**:
   - **Controlador (`routes.py`)**: Gestiona peticiones HTTP y renderizado de plantillas.
   - **Servicio (`service.py`)**: Orquesta la lógica de negocio, validaciones y transformación de datos.
   - **Repositorio (`repository.py`)**: Acceso exclusivo a SQLite y ejecución de consultas SQL.

---

## 🏗️ Arquitectura del Proyecto

El proyecto sigue el patrón **Application Factory** y **Blueprints** de Flask:

```text
Proyecto_Quick_Order/
│
├── app/
│   ├── __init__.py                # Fábrica de aplicaciones (create_app) y registro de Blueprints
│   ├── config.py                  # Configuraciones (Desarrollo, Pruebas con BD aislada)
│   ├── database.py                # Conexión, cierre y creación automática de SQLite
│   ├── schema.sql                 # Definición de tablas DDL (tabla producto)
│   ├── seed.py                    # Datos de prueba controlados
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   └── productos/
│   │       ├── __init__.py        # Exportaciones del módulo de productos
│   │       ├── routes.py          # Controlador: recibe HTTP y llama a service.py
│   │       ├── service.py         # Servicio: lógica de negocio y orquestación
│   │       └── repository.py      # Repositorio: consultas SQL sobre SQLite
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css         # Diseño visual moderno estilo fast-food POS
│   │   └── js/
│   │       └── main.js            # Lógica e interacciones del lado del cliente
│   │
│   └── templates/
│       ├── base.html              # Plantilla base (encabezado, navegación, pie)
│       └── productos/
│           └── catalogo.html      # Vista del catálogo, estado vacío y alertas
│
├── data/                          # Almacén de base de datos SQLite
│   ├── .gitkeep
│   ├── quick_order.db             # Base de datos de desarrollo (autocreada)
│   └── quick_order_test.db        # Base de datos aislada para pruebas
│
├── tests/
│   ├── __init__.py
│   └── test_productos.py          # Pruebas automatizadas (Normal, Límite, Error, Servicio, Repositorio)
│
├── requirements.txt               # Dependencias del proyecto (Flask)
├── run.py                         # Punto de entrada para ejecutar el servidor local
└── README.md                      # Documentación del sistema
```

---

## 🛠️ Tecnologías Utilizadas

- **Python 3.13**: Lenguaje base, robusto y legible.
- **Flask 3.x**: Microframework web modular y ligero con Blueprints.
- **SQLite 3**: Base de datos relacional serverless embebida.
- **HTML5, CSS3 y Vanilla JavaScript**: Interfaz limpia, responsiva y rápida para puntos de venta.

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

Abra su navegador web e ingrese a:
👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto incluye 7 pruebas automatizadas que cubren todos los escenarios:

1. **Caso Normal**: Con 3 productos activos y 1 inactivo, verifica que solo aparezcan los 3 activos.
2. **Caso Límite**: Sin productos activos, verifica que se muestre el mensaje de catálogo vacío.
3. **Caso de Error**: Simulación de fallo en la capa de datos/servicio, verificando mensaje controlado y código 500.
4. **Pruebas de Repositorio**: Filtrado estricto `WHERE activo = 1` y ordenamiento.
5. **Pruebas de Servicio**: Formateo, manejo de excepciones (`ProductoServiceError`) y validación de conexiones.

Para ejecutar todas las pruebas:

```powershell
.\venv\Scripts\python -m unittest discover -s tests -v
```
