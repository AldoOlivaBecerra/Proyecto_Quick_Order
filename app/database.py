"""
Módulo de Gestión de Base de Datos SQLite.
Administra la conexión por petición, cierre de conexiones y la inicialización
automática del esquema definido en schema.sql.
"""
import os
import sqlite3
import click
from flask import g, current_app

def get_db():
    """
    Obtiene o crea una conexión con la base de datos SQLite
    para el contexto de la petición actual.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        
        # Asegurar que el directorio de la base de datos exista si no es en memoria ni URI
        if not db_path.startswith(('file:', ':memory:')):
            dir_name = os.path.dirname(db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
        is_uri = db_path.startswith('file:')
        g.db = sqlite3.connect(
            db_path,
            uri=is_uri
        )
        # Permite acceder a las columnas por nombre (ej. fila['nombre'])
        g.db.row_factory = sqlite3.Row
        # Habilitar soporte de llaves foráneas en SQLite
        g.db.execute("PRAGMA foreign_keys = ON;")
        
    return g.db

def close_db(e=None):
    """
    Cierra la conexión con la base de datos al finalizar la petición.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """
    Ejecuta el archivo schema.sql para crear las tablas necesarias si no existen.
    """
    if app:
        with app.app_context():
            _execute_schema()
    else:
        _execute_schema()

def _execute_schema():
    """Función interna que lee y ejecuta schema.sql."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, mode='r', encoding='utf-8') as f:
        db.cursor().executescript(f.read())
    db.commit()

@click.command('init-db')
def init_db_command():
    """Comando de consola para inicializar la base de datos manualmente."""
    _execute_schema()
    click.echo('Base de datos inicializada correctamente.')

def init_app(app):
    """
    Registra el manejo de la base de datos en la aplicación Flask:
    - Cierre automático de conexiones.
    - Registro de comando CLI.
    - Verificación e inicialización automática de tablas al arrancar.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    
    # Inicialización automática de la base de datos al arrancar (solo fuera de pruebas)
    if not app.config.get('TESTING'):
        with app.app_context():
            _execute_schema()
