"""
Módulo de Productos para QUICK ORDER.
Exporta el blueprint de rutas y elementos clave del servicio.
"""
from app.modules.productos.routes import productos_bp
from app.modules.productos.service import obtener_catalogo_productos, ProductoServiceError

__all__ = ['productos_bp', 'obtener_catalogo_productos', 'ProductoServiceError']
