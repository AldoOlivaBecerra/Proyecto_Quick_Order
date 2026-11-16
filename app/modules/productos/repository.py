"""
Capa de Acceso a Datos (Repository) para el módulo de Productos.
Encapsula todas las consultas SQL directas sobre la tabla 'producto'.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Excepción personalizada para errores en la capa de datos."""
    pass

def obtener_productos_activos(db_conn):
    """
    Consulta y retorna únicamente los productos que se encuentren activos (activo = 1).
    
    Parámetros:
        db_conn (sqlite3.Connection): Conexión activa a la base de datos SQLite.
        
    Retorna:
        list[dict]: Lista de productos activos con sus campos:
                    producto_id, nombre, descripcion, activo.
                    
    Lanza:
        DatabaseError: En caso de fallo en la consulta o conexión con SQLite.
    """
    query = """
        SELECT producto_id, nombre, descripcion, activo
        FROM producto
        WHERE activo = 1
        ORDER BY nombre ASC;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query)
        filas = cursor.fetchall()
        
        # Convertir objetos Row de SQLite a diccionarios estándar
        productos = [
            {
                'producto_id': fila['producto_id'],
                'nombre': fila['nombre'],
                'descripcion': fila['descripcion'] if fila['descripcion'] else '',
                'activo': fila['activo']
            }
            for fila in filas
        ]
        return productos
        
    except sqlite3.Error as error:
        logger.error("Error al consultar productos activos en SQLite: %s", error)
        raise DatabaseError(f"No fue posible consultar los productos activos: {error}") from error
