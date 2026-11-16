"""
Módulo para poblar la base de datos con datos de prueba (Seed Data).
Inserta productos de prueba claramente identificados para verificar el funcionamiento
del catálogo (al menos 3 productos activos y 1 inactivo).
"""
import click
from app.database import get_db

PRODUCTOS_DE_PRUEBA = [
    (
        "[TEST] Hamburguesa Clásica con Queso",
        "Carne de res seleccionada 150g, queso cheddar fundido, lechuga fresca y tomate en pan brioche artesanal.",
        1
    ),
    (
        "[TEST] Papas Fritas Rústicas",
        "Porción grande de papas crujientes sazonadas con sal de mar y un toque de pimentón dulce.",
        1
    ),
    (
        "[TEST] Refresco de Cola Helado",
        "Bebida refrescante de 500 ml servida con hielo y rodaja de limón.",
        1
    ),
    (
        "[TEST - INACTIVO] Helado de Vainilla de Temporada",
        "Postre frío de temporada no disponible temporalmente en el menú.",
        0
    ),
]

def seed_test_data(db=None):
    """
    Inserta los datos de prueba en la tabla producto si esta se encuentra vacía.
    Retorna la cantidad de productos insertados.
    """
    if db is None:
        db = get_db()
        
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM producto;")
    total = cursor.fetchone()['total']
    
    if total == 0:
        cursor.executemany(
            """
            INSERT INTO producto (nombre, descripcion, activo)
            VALUES (?, ?, ?);
            """,
            PRODUCTOS_DE_PRUEBA
        )
        db.commit()
        return len(PRODUCTOS_DE_PRUEBA)
    
    return 0

@click.command('seed-db')
def seed_db_command():
    """Comando CLI para cargar datos de prueba manualmente."""
    db = get_db()
    insertados = seed_test_data(db)
    if insertados > 0:
        click.echo(f"Se insertaron {insertados} productos de prueba exitosamente.")
    else:
        click.echo("La base de datos ya contiene productos. No se realizaron cambios.")

def init_seed_app(app):
    """Registra el comando CLI de seed en la aplicación Flask."""
    app.cli.add_command(seed_db_command)
