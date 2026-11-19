"""
Módulo de Reportes de QUICK ORDER.
Exporta el Blueprint y las funciones clave del servicio de reportes.
"""
from app.modules.reportes.routes import reportes_bp
from app.modules.reportes.service import (
    obtener_reporte_mas_vendidos,
    ReporteServiceError,
    ReporteDatabaseError
)

__all__ = [
    'reportes_bp',
    'obtener_reporte_mas_vendidos',
    'ReporteServiceError',
    'ReporteDatabaseError'
]
