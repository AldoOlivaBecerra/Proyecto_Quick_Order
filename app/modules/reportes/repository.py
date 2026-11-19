"""
Capa de Acceso a Datos (Repository) para el módulo de Reportes.
Ejecuta exclusivamente consultas analíticas de lectura sobre SQLite.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Excepción para errores de bajo nivel en consultas del repositorio de reportes."""
    pass

def obtener_productos_mas_vendidos(db_conn):
    """
    Ejecuta la consulta analítica para obtener la cantidad total vendida por producto.
    
    Reglas estrictas:
    - Considera ÚNICAMENTE comandas con estado 'finalizada'.
    - Excluye comandas 'pendiente', 'en preparación' y 'cancelada'.
    - Suma las cantidades acumuladas de detalle_comanda.
    - Ordena de mayor a menor cantidad vendida (total_vendido DESC).
    - Desempata alfabéticamente por nombre de producto (p.nombre ASC).
    
    Retorna una lista de diccionarios con la estructura:
    [
        {
            'producto_id': int,
            'nombre': str,
            'descripcion': str,
            'activo': int,
            'total_vendido': int,
            'total_comandas': int
        },
        ...
    ]
    """
    query = """
        SELECT 
            p.producto_id,
            p.nombre,
            p.descripcion,
            p.activo,
            SUM(dc.cantidad) AS total_vendido,
            COUNT(DISTINCT c.comanda_id) AS total_comandas
        FROM producto p
        INNER JOIN detalle_comanda dc ON p.producto_id = dc.producto_id
        INNER JOIN comanda c ON dc.comanda_id = c.comanda_id
        WHERE c.estado = 'finalizada'
        GROUP BY p.producto_id, p.nombre, p.descripcion, p.activo
        ORDER BY total_vendido DESC, p.nombre ASC;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        resultado = []
        for row in rows:
            resultado.append({
                'producto_id': row['producto_id'],
                'nombre': row['nombre'],
                'descripcion': row['descripcion'],
                'activo': row['activo'],
                'total_vendido': int(row['total_vendido']),
                'total_comandas': int(row['total_comandas'])
            })
        return resultado
    except sqlite3.Error as err:
        logger.error("Error al ejecutar consulta de productos más vendidos: %s", err)
        raise DatabaseError(f"Error en SQLite al consultar productos más vendidos: {err}") from err
