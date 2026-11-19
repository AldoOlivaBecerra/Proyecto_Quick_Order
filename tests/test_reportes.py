"""
Pruebas Automatizadas para el Módulo de Reportes (Productos Más Vendidos).
Cubre:
- Cálculo exacto de cantidades totales vendidas por producto.
- Ordenamiento estricto de mayor a menor demanda (total_vendido DESC).
- Desempate alfabético por nombre de producto ante igual cantidad vendida.
- Exclusión categórica de comandas en estado pendiente, en preparación y cancelada.
- Manejo seguro de casos límite (cero ventas, base vacía sin división por cero).
- Respeto a las ventas históricas de productos actualmente inactivos.
- Validación de conexión activa y manejo de errores de base de datos.
- Renderizado de interfaz HTML (GET /reportes/) con KPIs y tablas.
"""
import os
import tempfile
import unittest
from unittest.mock import patch
from app import create_app
from app.database import get_db, init_db
from app.modules.reportes.service import (
    obtener_reporte_mas_vendidos,
    ReporteServiceError,
    ReporteDatabaseError
)
from app.modules.reportes.repository import DatabaseError

class TestModuloReportes(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el módulo de Reportes."""

    def setUp(self):
        """Configura una base de datos temporal SQLite aislada para cada prueba."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = create_app('testing')
        self.app.config['DATABASE'] = self.db_path
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            db = get_db()
            cursor = db.cursor()
            # Insertar productos de prueba base
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (1, 'Hamburguesa Doble Carne', 'Con queso cheddar', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (2, 'Papas Fritas Medianas', 'Crujientes con sal', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (3, 'Refresco de Cola 600ml', 'Frío con hielo', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (4, 'Aros de Cebolla', 'Empanizados', 1);"
            )
            db.commit()

    def tearDown(self):
        """Limpia la base de datos temporal al terminar cada prueba."""
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # 1. Cálculo correcto y ordenamiento descendente
    # -------------------------------------------------------------------------
    def test_reporte_calculo_correcto_orden_descendente(self):
        """
        Verifica que el reporte sume correctamente las cantidades vendidas de cada
        producto y las ordene estrictamente de mayor a menor cantidad vendida.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Comanda 1 (finalizada): 4 Hamburguesas (id 1) y 2 Papas (id 2)
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 1, 4);")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 2, 2);")

            # Comanda 2 (finalizada): 1 Hamburguesa (id 1) y 6 Refrescos (id 3)
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (2, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (2, 1, 1);")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (2, 3, 6);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)
            prods = reporte['productos']

            # Totales esperados:
            # Refresco (id 3): 6 unidades
            # Hamburguesa (id 1): 4 + 1 = 5 unidades
            # Papas (id 2): 2 unidades
            # Total general: 13 unidades
            self.assertEqual(len(prods), 3)
            self.assertEqual(reporte['total_unidades_vendidas'], 13)
            self.assertEqual(reporte['total_productos_distintos'], 3)

            # Validar orden descendente
            self.assertEqual(prods[0]['producto_id'], 3)
            self.assertEqual(prods[0]['total_vendido'], 6)
            self.assertEqual(prods[0]['ranking'], 1)

            self.assertEqual(prods[1]['producto_id'], 1)
            self.assertEqual(prods[1]['total_vendido'], 5)
            self.assertEqual(prods[1]['ranking'], 2)

            self.assertEqual(prods[2]['producto_id'], 2)
            self.assertEqual(prods[2]['total_vendido'], 2)
            self.assertEqual(prods[2]['ranking'], 3)

            # Validar producto estrella
            self.assertIsNotNone(reporte['producto_estrella'])
            self.assertEqual(reporte['producto_estrella']['producto_id'], 3)

            # Validar porcentajes de participación (6/13 = 46.2%, 5/13 = 38.5%, 2/13 = 15.4%)
            self.assertAlmostEqual(prods[0]['porcentaje'], 46.2, places=1)
            self.assertAlmostEqual(prods[1]['porcentaje'], 38.5, places=1)
            self.assertAlmostEqual(prods[2]['porcentaje'], 15.4, places=1)

    # -------------------------------------------------------------------------
    # 2. Exclusión categórica de comandas NO finalizadas
    # -------------------------------------------------------------------------
    def test_exclusion_estricta_comandas_no_finalizadas(self):
        """
        Verifica que el reporte contabilice ÚNICAMENTE las comandas con estado 'finalizada',
        excluyendo de forma absoluta las comandas 'pendiente', 'en preparación' y 'cancelada'.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Comanda 1: PENDIENTE con 20 Papas (id 2) -> NO DEBE CONTARSE
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'pendiente');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 2, 20);")

            # Comanda 2: EN PREPARACIÓN con 15 Hamburguesas (id 1) -> NO DEBE CONTARSE
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (2, 'en preparación');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (2, 1, 15);")

            # Comanda 3: CANCELADA con 30 Refrescos (id 3) -> NO DEBE CONTARSE
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (3, 'cancelada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (3, 3, 30);")

            # Comanda 4: FINALIZADA con 3 Hamburguesas (id 1) y 1 Refresco (id 3) -> SÍ DEBE CONTARSE
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (4, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (4, 1, 3);")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (4, 3, 1);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)
            prods = reporte['productos']

            # Solo deben existir 2 productos en el reporte con un total de 4 unidades
            self.assertEqual(reporte['total_unidades_vendidas'], 4)
            self.assertEqual(len(prods), 2)

            # Hamburguesa: solo 3 unidades (las 15 de 'en preparación' se excluyeron)
            self.assertEqual(prods[0]['producto_id'], 1)
            self.assertEqual(prods[0]['total_vendido'], 3)

            # Refresco: solo 1 unidad (las 30 de 'cancelada' se excluyeron)
            self.assertEqual(prods[1]['producto_id'], 3)
            self.assertEqual(prods[1]['total_vendido'], 1)

            # Papas: 0 unidades finalizadas, no debe figurar en el reporte
            ids_reporte = [p['producto_id'] for p in prods]
            self.assertNotIn(2, ids_reporte)

    # -------------------------------------------------------------------------
    # 3. Caso límite: Cero ventas / sin comandas finalizadas
    # -------------------------------------------------------------------------
    def test_reporte_sin_comandas_finalizadas(self):
        """
        Verifica que ante la ausencia de ventas finalizadas el servicio responda con
        totales en cero y lista vacía, sin generar excepciones ni división por cero.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Solo hay una comanda pendiente
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'pendiente');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 1, 5);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)

            self.assertEqual(reporte['productos'], [])
            self.assertEqual(reporte['total_unidades_vendidas'], 0)
            self.assertEqual(reporte['total_productos_distintos'], 0)
            self.assertIsNone(reporte['producto_estrella'])

    # -------------------------------------------------------------------------
    # 4. Desempate alfabético consistente ante empate de ventas
    # -------------------------------------------------------------------------
    def test_desempate_alfabetico(self):
        """
        Verifica que ante la misma cantidad total vendida, los productos se ordenen
        alfabéticamente de forma consistente y determinista por su nombre.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Comanda finalizada donde 'Aros de Cebolla' y 'Hamburguesa...' tienen ambos 5 unidades
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 1, 5);")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 4, 5);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)
            prods = reporte['productos']

            self.assertEqual(len(prods), 2)
            self.assertEqual(prods[0]['total_vendido'], 5)
            self.assertEqual(prods[1]['total_vendido'], 5)

            # 'Aros de Cebolla' debe aparecer primero que 'Hamburguesa Doble Carne' por orden alfabético
            self.assertEqual(prods[0]['nombre'], 'Aros de Cebolla')
            self.assertEqual(prods[1]['nombre'], 'Hamburguesa Doble Carne')

    # -------------------------------------------------------------------------
    # 5. Múltiples detalles del mismo producto en comandas finalizadas
    # -------------------------------------------------------------------------
    def test_acumulacion_multiples_detalles_mismo_producto(self):
        """
        Verifica que SUM(dc.cantidad) agrupe correctamente múltiples registros
        del mismo producto repartidos en diversas comandas finalizadas.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 2, 3);")

            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (2, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (2, 2, 4);")

            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (3, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (3, 2, 1);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)
            prods = reporte['productos']

            self.assertEqual(len(prods), 1)
            self.assertEqual(prods[0]['producto_id'], 2)
            self.assertEqual(prods[0]['total_vendido'], 8) # 3 + 4 + 1
            self.assertEqual(prods[0]['total_comandas'], 3)

    # -------------------------------------------------------------------------
    # 6. Historial de ventas para productos actualmente inactivos
    # -------------------------------------------------------------------------
    def test_producto_inactivo_con_ventas_historicas(self):
        """
        Verifica que las ventas históricas de un producto no se pierdan ni se
        eliminen del reporte analítico si dicho producto fue posteriormente inactivado.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Insertar producto inactivo con ventas
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (5, 'Postre de Fresa Descontinuado', 'Exclusivo verano', 0);"
            )
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 5, 7);")
            db.commit()

            reporte = obtener_reporte_mas_vendidos(db)
            prods = reporte['productos']

            self.assertEqual(len(prods), 1)
            self.assertEqual(prods[0]['producto_id'], 5)
            self.assertEqual(prods[0]['activo'], 0)
            self.assertEqual(prods[0]['total_vendido'], 7)

    # -------------------------------------------------------------------------
    # 7. Validación de conexión nula en el servicio
    # -------------------------------------------------------------------------
    def test_servicio_rechaza_conexion_nula(self):
        """
        Verifica que la capa de servicio arroje ReporteServiceError si se invoca con None.
        """
        with self.assertRaises(ReporteServiceError):
            obtener_reporte_mas_vendidos(None)

    # -------------------------------------------------------------------------
    # 8. Manejo de error de base de datos en capa de servicio
    # -------------------------------------------------------------------------
    @patch('app.modules.reportes.repository.obtener_productos_mas_vendidos')
    def test_servicio_manejo_error_repositorio(self, mock_repo):
        """
        Verifica que la capa de servicio capture DatabaseError y emita ReporteDatabaseError.
        """
        mock_repo.side_effect = DatabaseError("Fallo inducido en la base de datos")

        with self.app.app_context():
            db = get_db()
            with self.assertRaises(ReporteDatabaseError):
                obtener_reporte_mas_vendidos(db)

    # -------------------------------------------------------------------------
    # 9. Verificación de endpoints HTTP y Renderizado de Plantilla (GET /reportes/)
    # -------------------------------------------------------------------------
    def test_endpoint_pantalla_reportes_exitoso(self):
        """
        Verifica que GET /reportes/ devuelva HTTP 200 y renderice correctamente
        los datos, columnas, cantidades y elementos visuales esperados.
        """
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO comanda (comanda_id, estado) VALUES (1, 'finalizada');")
            cursor.execute("INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad) VALUES (1, 1, 10);")
            db.commit()

        # Probar ruta raíz del blueprint
        response = self.client.get('/reportes/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Reporte de Ventas: Productos Más Vendidos", html)
        self.assertIn("Total Unidades Vendidas", html)
        self.assertIn("10", html)
        self.assertIn("Hamburguesa Doble Carne", html)
        self.assertIn("🥇 #1", html)

        # Probar alias /reportes/mas-vendidos
        response_alias = self.client.get('/reportes/mas-vendidos')
        self.assertEqual(response_alias.status_code, 200)

    # -------------------------------------------------------------------------
    # 10. Verificación de pantalla con estado vacío
    # -------------------------------------------------------------------------
    def test_endpoint_pantalla_reportes_estado_vacio(self):
        """
        Verifica que cuando no existen ventas, la pantalla muestre el mensaje de estado vacío
        sin arrojar error HTTP 500 ni inconsistencias visuales.
        """
        response = self.client.get('/reportes/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("Aún no hay ventas registradas", html)
        self.assertIn("Ninguno", html)
        self.assertIn("Ir a Cocina a Finalizar Órdenes", html)

    # -------------------------------------------------------------------------
    # 11. Manejo controlado de fallos HTTP 500 en rutas
    # -------------------------------------------------------------------------
    @patch('app.modules.reportes.routes.obtener_reporte_mas_vendidos')
    def test_endpoint_pantalla_reportes_error_controlado(self, mock_service):
        """
        Verifica que ante una excepción en la capa de servicio, la ruta capture
        el error y devuelva HTTP 500 con un mensaje entendible para el usuario.
        """
        mock_service.side_effect = ReporteServiceError("Error de prueba en el servicio")

        response = self.client.get('/reportes/')
        self.assertEqual(response.status_code, 500)
        html = response.get_data(as_text=True)

        self.assertIn("No fue posible conectar o consultar la base de datos de reportes", html)
