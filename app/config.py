"""
Módulo de Configuración de QUICK ORDER.
Permite definir diferentes entornos (desarrollo, pruebas, producción).
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Configuración base común a todos los entornos."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'quick-order-dev-secret-key-2026')
    DATABASE = os.path.join(BASE_DIR, 'data', 'quick_order.db')
    TESTING = False
    DEBUG = False

class DevelopmentConfig(Config):
    """Configuración para el entorno de desarrollo local."""
    DEBUG = True

class TestingConfig(Config):
    """Configuración para ejecución de pruebas automatizadas."""
    TESTING = True
    DEBUG = True
    # Base de datos aislada para pruebas (evita pérdida de esquema por conexiones efímeras)
    DATABASE = os.path.join(BASE_DIR, 'data', 'quick_order_test.db')

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
