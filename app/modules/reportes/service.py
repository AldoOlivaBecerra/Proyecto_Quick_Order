"""
Capa de Lógica de Negocio (Service) para el módulo de Reportes.
Coordina la obtención de datos analíticos, calcula métricas acumuladas y porcentajes,
y controla los casos límite (sin ventas o conexiones inválidas).
"""
import logging
from app.modules.reportes import repository
from app.modules.reportes.repository import DatabaseError

logger = logging.getLogger(__name__)

class ReporteServiceError(Exception):
    """Excepción base para errores en el servicio de reportes."""
    pass

class ReporteDatabaseError(ReporteServiceError):
    """Excepción lanzada cuando ocurre un error de persistencia o SQLite."""
    pass

def obtener_reporte_mas_vendidos(db_conn):
    """
    Obtiene el reporte consolidado de productos más vendidos y calcula KPIs del negocio.
    
    Reglas de negocio:
    - Se requiere una conexión activa a SQLite.
    - Únicamente se computan ventas provenientes de comandas finalizadas.
    - Si no existen ventas, retorna totales en 0 y lista vacía sin arrojar excepciones.
    - Calcula porcentaje de contribución de cada producto sobre el total general.
    - Asigna número de ranking correlativo según la cantidad vendida.
    
    Retorna un diccionario con:
    {
        'productos': [
            {
                'ranking': int,
                'producto_id': int,
                'nombre': str,
                'descripcion': str,
                'activo': int,
                'total_vendido': int,
                'total_comandas': int,
                'porcentaje': float
            },
            ...
        ],
        'total_unidades_vendidas': int,
        'total_productos_distintos': int,
        'producto_estrella': dict | None
    }
    """
    if db_conn is None:
        logger.error("Se intentó generar el reporte de ventas sin una conexión activa a la base de datos.")
        raise ReporteServiceError("Se requiere una conexión válida a la base de datos.")

    try:
        productos_raw = repository.obtener_productos_mas_vendidos(db_conn)
    except DatabaseError as err:
        logger.error("Fallo al obtener datos del repositorio de reportes: %s", err)
        raise ReporteDatabaseError(f"Error al consultar el repositorio de reportes: {err}") from err

    total_unidades_vendidas = sum(item['total_vendido'] for item in productos_raw)
    total_productos_distintos = len(productos_raw)
    
    productos_enriquecidos = []
    for idx, item in enumerate(productos_raw, start=1):
        porcentaje = 0.0
        if total_unidades_vendidas > 0:
            porcentaje = round((item['total_vendido'] / total_unidades_vendidas) * 100, 1)
            
        productos_enriquecidos.append({
            'ranking': idx,
            'producto_id': item['producto_id'],
            'nombre': item['nombre'],
            'descripcion': item['descripcion'],
            'activo': item['activo'],
            'total_vendido': item['total_vendido'],
            'total_comandas': item['total_comandas'],
            'porcentaje': porcentaje
        })

    producto_estrella = productos_enriquecidos[0] if productos_enriquecidos else None

    return {
        'productos': productos_enriquecidos,
        'total_unidades_vendidas': total_unidades_vendidas,
        'total_productos_distintos': total_productos_distintos,
        'producto_estrella': producto_estrella
    }
