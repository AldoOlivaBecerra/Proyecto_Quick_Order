"""
Fábrica de Aplicaciones (Application Factory) de QUICK ORDER.
Permite instanciar la aplicación Flask con distintas configuraciones y módulos.
"""
from flask import Flask
from app.config import config_by_name
from app.database import init_app, get_db
from app.seed import init_seed_app, seed_test_data
from app.modules.productos import productos_bp
from app.modules.comandas import comandas_bp
from app.modules.cocina import cocina_bp

def create_app(config_name='default'):
    """
    Crea y configura una instancia de la aplicación Flask.
    
    Parámetros:
        config_name (str): Nombre del entorno ('development', 'testing', 'default').
        
    Retorna:
        Flask: Instancia configurada de la aplicación.
    """
    app = Flask(__name__)
    
    # Cargar configuración correspondiente
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)
    
    # Inicializar base de datos y comandos CLI
    init_app(app)
    init_seed_app(app)
    
    # En desarrollo, asegurar la inserción de datos de prueba si la base de datos está vacía
    if not app.config.get('TESTING'):
        with app.app_context():
            try:
                db = get_db()
                seed_test_data(db)
            except Exception as e:
                app.logger.warning("No se pudo autosembrar datos de prueba iniciales: %s", e)
                
    # Registro de módulos (Blueprints)
    app.register_blueprint(productos_bp)
    app.register_blueprint(comandas_bp)
    app.register_blueprint(cocina_bp)
    
    return app
