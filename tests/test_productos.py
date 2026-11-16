"""
Pruebas Automatizadas para el Módulo de Productos de QUICK ORDER.
Cubre los escenarios requeridos:
- PRUEBA 1: Caso Normal (3 productos activos, 1 inactivo -> solo se muestran los 3 activos).
- PRUEBA 2: Caso Límite (sin productos activos -> mensaje de catálogo vacío).
- PRUEBA 3: Caso de Error (fallo de base de datos reportado por service -> respuesta 500 controlada).
- PRUEBAS UNITARIAS DE SERVICIO Y REPOSITORIO (separación arquitectónica en 3 capas).
"""
import os
import tempfile
import unittest
from unittest.mock import patch
from app import create_app
from app.database import get_db, init_db
from app.modules.productos.repository import obtener_productos_activos, DatabaseError
from app.modules.productos.service import obtener_catalogo_productos, ProductoServiceError

class TestModuloProductos(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el catálogo de productos."""

    def setUp(self):
        """Configura un entorno de pruebas aislado con base de datos temporal SQLite."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = create_app('testing')
        self.app.config['DATABASE'] = self.db_path
        self.client = self.app.test_client()

        with self.app.app_context():
            # Crear la estructura de tablas para la prueba
            init_db()

    def tearDown(self):
        """Limpia y elimina la base de datos temporal después de cada prueba."""
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # PRUEBA 1 - CASO NORMAL
    # -------------------------------------------------------------------------
    def test_caso_normal_productos_activos(self):
        """
        PRUEBA 1 - CASO NORMAL:
        Existen 3 productos activos y 1 producto inactivo.
        Resultado esperado:
        - Código de estado HTTP 200.
        - Aparecen únicamente los tres productos activos en el catálogo.
        - El producto inactivo NO debe aparecer en la interfaz.
        """
        with self.app.app_context():
            db = get_db()
            db.executemany(
                "INSERT INTO producto (nombre, descripcion, activo) VALUES (?, ?, ?);",
                [
                    ("[TEST] Hamburguesa Clásica", "Carne 150g con queso cheddar.", 1),
                    ("[TEST] Papas Fritas", "Papas crujientes con sal marina.", 1),
                    ("[TEST] Refresco de Cola", "Refresco frío de 500ml.", 1),
                    ("[TEST - INACTIVO] Helado Temporal", "Postre no disponible.", 0)
                ]
            )
            db.commit()

        # Realizar petición GET al catálogo
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200, "La respuesta debe ser HTTP 200.")
        
        # Verificar que aparecen los 3 productos activos
        self.assertIn("[TEST] Hamburguesa Clásica", html, "Debe mostrarse la hamburguesa activa.")
        self.assertIn("[TEST] Papas Fritas", html, "Deben mostrarse las papas fritas activas.")
        self.assertIn("[TEST] Refresco de Cola", html, "Debe mostrarse el refresco activo.")
        
        # Verificar que sus descripciones se muestran
        self.assertIn("Carne 150g con queso cheddar.", html)
        self.assertIn("Papas crujientes con sal marina.", html)
        self.assertIn("Refresco frío de 500ml.", html)
        
        # Verificar que el producto inactivo NO aparece
        self.assertNotIn("[TEST - INACTIVO] Helado Temporal", html, "El producto inactivo no debe aparecer.")
        self.assertNotIn("Postre no disponible.", html, "La descripción del inactivo no debe aparecer.")

    # -------------------------------------------------------------------------
    # PRUEBA 2 - CASO LÍMITE
    # -------------------------------------------------------------------------
    def test_caso_limite_sin_productos_activos(self):
        """
        PRUEBA 2 - CASO LÍMITE:
        No existen productos activos (base de datos vacía o solo contiene inactivos).
        Resultado esperado:
        - Código de estado HTTP 200.
        - Aparece el mensaje 'No hay productos disponibles'.
        - No se renderizan tarjetas de productos.
        """
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO producto (nombre, descripcion, activo) VALUES (?, ?, ?);",
                ("[TEST - INACTIVO] Solo Inactivo", "Descripción inactiva.", 0)
            )
            db.commit()

        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200, "La respuesta debe ser HTTP 200.")
        self.assertIn("No hay productos disponibles", html, "Debe mostrar el mensaje de catálogo vacío.")
        self.assertNotIn("product-card", html, "No deben existir tarjetas de productos cuando no hay activos.")
        self.assertNotIn("[TEST - INACTIVO] Solo Inactivo", html, "El producto inactivo no debe listarse.")

    # -------------------------------------------------------------------------
    # PRUEBA 3 - CASO DE ERROR
    # -------------------------------------------------------------------------
    def test_caso_error_base_datos(self):
        """
        PRUEBA 3 - CASO DE ERROR:
        Se presenta un problema al acceder o consultar la base de datos reportado por service.
        Resultado esperado:
        - El sistema responde de manera controlada (HTTP 500).
        - Muestra un mensaje descriptivo de error en la interfaz.
        - La aplicación no genera excepciones no atrapadas.
        """
        # Simular una falla en la capa de servicio
        with patch('app.modules.productos.routes.obtener_catalogo_productos') as mock_service:
            mock_service.side_effect = ProductoServiceError("Error simulado en la capa de servicio")

            response = self.client.get('/')
            html = response.get_data(as_text=True)

            self.assertEqual(response.status_code, 500, "Debe responder con código 500 controlado.")
            self.assertIn("Error de Conexión o Consulta", html, "Debe informar el problema al usuario.")
            self.assertIn("No fue posible conectar o consultar la base de datos", html)
            self.assertNotIn("Traceback", html, "No debe exponer trazas sin procesar al usuario.")

    # -------------------------------------------------------------------------
    # PRUEBAS ESPECÍFICAS DE LA CAPA SERVICE
    # -------------------------------------------------------------------------
    def test_service_obtiene_catalogo_exitoso(self):
        """Verifica que service.py coordine adecuadamente los datos y aplique reglas."""
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO producto (nombre, descripcion, activo) VALUES (?, ?, ?);",
                ("  Hamburguesa Trim  ", "  Descripción con espacios  ", 1)
            )
            db.commit()

            resultado = obtener_catalogo_productos(db)
            self.assertEqual(len(resultado), 1)
            self.assertEqual(resultado[0]['nombre'], "Hamburguesa Trim")
            self.assertEqual(resultado[0]['descripcion'], "Descripción con espacios")

    def test_service_manejo_error_repositorio(self):
        """Verifica que service.py capture DatabaseError y emita ProductoServiceError."""
        with patch('app.modules.productos.service.repo_obtener_productos_activos') as mock_repo:
            mock_repo.side_effect = DatabaseError("Fallo simulado a nivel SQLite")
            
            with self.assertRaises(ProductoServiceError):
                with self.app.app_context():
                    db = get_db()
                    obtener_catalogo_productos(db)

    def test_service_sin_conexion(self):
        """Verifica que service.py rechace conexiones nulas."""
        with self.assertRaises(ProductoServiceError):
            obtener_catalogo_productos(None)

    # -------------------------------------------------------------------------
    # PRUEBAS ESPECÍFICAS DE LA CAPA REPOSITORY
    # -------------------------------------------------------------------------
    def test_repository_filtro_y_ordenamiento(self):
        """Verifica que la función del repositorio filtre activo=1 y ordene por nombre."""
        with self.app.app_context():
            db = get_db()
            db.executemany(
                "INSERT INTO producto (nombre, descripcion, activo) VALUES (?, ?, ?);",
                [
                    ("Bebida B", "Desc B", 1),
                    ("Comida A", "Desc A", 1),
                    ("Inactivo Z", "Desc Z", 0),
                ]
            )
            db.commit()

            productos = obtener_productos_activos(db)

            self.assertEqual(len(productos), 2)
            self.assertEqual(productos[0]['nombre'], "Bebida B")
            self.assertEqual(productos[1]['nombre'], "Comida A")
            for p in productos:
                self.assertEqual(p['activo'], 1)

if __name__ == '__main__':
    unittest.main()
