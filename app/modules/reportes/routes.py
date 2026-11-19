"""
Controlador y Rutas del módulo de Reportes.
Gestiona las peticiones HTTP y la presentación del reporte analítico de ventas.
Se comunica exclusivamente con la capa de servicio (service.py).
"""
import logging
from flask import Blueprint, render_template, current_app
from app.database import get_db
from app.modules.reportes.service import (
    obtener_reporte_mas_vendidos,
    ReporteServiceError
)

logger = logging.getLogger(__name__)

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/', methods=['GET'])
@reportes_bp.route('/mas-vendidos', methods=['GET'])
def reporte_mas_vendidos():
    """
    Ruta principal del reporte de productos más vendidos.
    Solicita a la capa de servicio el consolidado acumulado de ventas
    obtenido exclusivamente de comandas finalizadas.
    """
    error_mensaje = None
    reporte = {
        'productos': [],
        'total_unidades_vendidas': 0,
        'total_productos_distintos': 0,
        'producto_estrella': None
    }
    status_code = 200

    try:
        db = get_db()
        reporte = obtener_reporte_mas_vendidos(db)
    except ReporteServiceError as err:
        current_app.logger.error("Error controlado en capa de servicio de reportes: %s", err)
        error_mensaje = "No fue posible conectar o consultar la base de datos de reportes. Intente más tarde."
        status_code = 500
    except Exception as err:
        current_app.logger.exception("Error inesperado en controlador de reportes: %s", err)
        error_mensaje = "Ocurrió un error inesperado al generar el reporte de productos más vendidos."
        status_code = 500

    return render_template(
        'reportes/mas_vendidos.html',
        reporte=reporte,
        error_mensaje=error_mensaje
    ), status_code
