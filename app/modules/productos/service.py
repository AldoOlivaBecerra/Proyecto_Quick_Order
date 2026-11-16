"""
Capa de Lógica de Negocio (Service) para el módulo de Productos.
Orquesta y coordina las operaciones del catálogo de productos,
desacoplando el controlador (routes.py) del acceso a datos (repository.py).
"""
import logging
from app.modules.productos.repository import (
    obtener_productos_activos as repo_obtener_productos_activos,
    DatabaseError
)

logger = logging.getLogger(__name__)

class ProductoServiceError(Exception):
    """Excepción para errores de lógica de negocio o fallos en el servicio de productos."""
    pass

def obtener_catalogo_productos(db_conn):
    """
    Obtiene y procesa los productos activos para el catálogo de QUICK ORDER.
    
    Aplica las reglas de negocio del primer incremento:
    - Consulta únicamente productos activos.
    - Asegura la consistencia en nombres y descripciones.
    - Maneja y transforma excepciones de base de datos a nivel de servicio.
    
    Parámetros:
        db_conn (sqlite3.Connection): Conexión activa a SQLite.
        
    Retorna:
        list[dict]: Lista de productos activos formateados para la presentación.
        
    Lanza:
        ProductoServiceError: Si ocurre un error al consultar o procesar los datos.
    """
    if db_conn is None:
        logger.error("Se intentó consultar el catálogo sin una conexión válida a SQLite.")
        raise ProductoServiceError("Conexión a base de datos no disponible.")

    try:
        productos = repo_obtener_productos_activos(db_conn)
        
        # Regla de negocio / Presentación: asegurar que cada producto tenga estructura íntegra
        catalogo = []
        for p in productos:
            catalogo.append({
                'producto_id': p['producto_id'],
                'nombre': p['nombre'].strip() if p.get('nombre') else '',
                'descripcion': p['descripcion'].strip() if p.get('descripcion') else '',
                'activo': p.get('activo', 1)
            })
            
        return catalogo

    except DatabaseError as db_err:
        logger.error("Error en servicio al obtener productos desde el repositorio: %s", db_err)
        raise ProductoServiceError(f"Error de servicio al consultar productos: {db_err}") from db_err
    except Exception as exc:
        logger.exception("Error inesperado en servicio de productos: %s", exc)
        raise ProductoServiceError(f"Error inesperado al procesar el catálogo: {exc}") from exc
