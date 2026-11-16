"""
Controlador y Rutas del módulo de Productos.
Gestiona las peticiones HTTP y la presentación del catálogo de productos.
Se comunica exclusivamente con la capa de servicio (service.py).
"""
from flask import Blueprint, render_template, current_app
from app.database import get_db
from app.modules.productos.service import (
    obtener_catalogo_productos,
    ProductoServiceError
)

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/')
@productos_bp.route('/productos')
def catalogo():
    """
    Ruta principal del catálogo de productos.
    Solicita a la capa de servicio el catálogo de productos activos.
    Maneja de forma controlada los errores reportados por el servicio.
    """
    error_mensaje = None
    productos = []
    status_code = 200

    try:
        db = get_db()
        # Invocación exclusiva a la capa de servicio
        productos = obtener_catalogo_productos(db)
    except ProductoServiceError as err:
        current_app.logger.error("Error controlado en capa de servicio: %s", err)
        error_mensaje = "No fue posible conectar o consultar la base de datos de productos. Intente más tarde."
        status_code = 500
    except Exception as err:
        current_app.logger.exception("Error inesperado en controlador de productos: %s", err)
        error_mensaje = "Ocurrió un error inesperado al procesar el catálogo de productos."
        status_code = 500

    return render_template(
        'productos/catalogo.html',
        productos=productos,
        error_mensaje=error_mensaje
    ), status_code
