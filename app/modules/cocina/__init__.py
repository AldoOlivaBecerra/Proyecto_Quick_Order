"""
Módulo de Cocina de QUICK ORDER (KDS).
Exporta el Blueprint y las funciones clave de servicio.
"""
from app.modules.cocina.routes import cocina_bp
from app.modules.cocina.service import (
    obtener_comandas_cocina,
    iniciar_preparacion,
    finalizar_preparacion,
    CocinaServiceError,
    CocinaComandaNoEncontradaError,
    CocinaTransicionInvalidaError,
    CocinaConcurrenciaError
)

__all__ = [
    'cocina_bp',
    'obtener_comandas_cocina',
    'iniciar_preparacion',
    'finalizar_preparacion',
    'CocinaServiceError',
    'CocinaComandaNoEncontradaError',
    'CocinaTransicionInvalidaError',
    'CocinaConcurrenciaError'
]
