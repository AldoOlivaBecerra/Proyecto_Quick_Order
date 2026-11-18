"""
Pruebas Automatizadas para el Módulo de Comandas de QUICK ORDER.
Cubre los 10 escenarios obligatorios del Segundo Incremento:
- CASO 1: Crear comanda correctamente (2 productos activos, cantidades válidas -> estado pendiente).
- CASO 2: Comanda vacía (sin productos -> rechazada).
- CASO 3: Cantidad inválida (cantidad <= 0 -> rechazada).
- CASO 4: Consultar comanda (se muestran productos, cantidades y especificaciones).
- CASO 5: Modificar comanda pendiente (cambio de cantidad o especificación -> guardada correctamente).
- CASO 6: Modificar comanda no pendiente (en preparación o finalizada -> rechazada).
- CASO 7: Cancelar comanda pendiente (cambia a 'cancelada' y conserva sus registros).
- CASO 8: Cancelar comanda no pendiente (en preparación o finalizada -> rechazada).
- CASO 9: Integridad referencial (producto inexistente -> rechazada).
- CASO 10: Persistencia (datos permanecen en SQLite al consultar nuevamente).
- Extra: Rechazo de productos inactivos al crear o modificar comandas.
"""
import os
import tempfile
import sqlite3
import unittest
from app import create_app
from app.database import get_db, init_db
from app.modules.comandas.service import (
    crear_comanda,
    obtener_comandas,
    obtener_detalle_comanda,
    modificar_comanda,
    cancelar_comanda,
    ComandaValidacionError,
    ComandaEstadoInvalidoError,
    ComandaNoEncontradaError
)

class TestModuloComandas(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el módulo de Comandas."""

    def setUp(self):
        """Configura un entorno aislado con base de datos temporal SQLite para cada prueba."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = create_app('testing')
        self.app.config['DATABASE'] = self.db_path
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            db = get_db()
            # Insertar productos de prueba base
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (1, '[TEST] Hamburguesa', 'Carne 150g', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (2, '[TEST] Papas Fritas', 'Papas crujientes', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (3, '[TEST - INACTIVO] Helado', 'No disponible', 0);"
            )
            db.commit()

    def tearDown(self):
        """Limpia y elimina la base de datos temporal."""
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # CASO 1 — Crear comanda correctamente
    # -------------------------------------------------------------------------
    def test_caso_1_crear_comanda_correctamente(self):
        """
        Se agregan dos productos activos con cantidades válidas.
        Resultado esperado: la comanda se guarda con estado 'pendiente'.
        """
        items = [
            {'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Sin cebolla'},
            {'producto_id': 2, 'cantidad': 1, 'especificaciones': 'Extra salsa'}
        ]

        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, items)
            self.assertGreater(comanda_id, 0)

            comanda = obtener_detalle_comanda(db, comanda_id)
            self.assertEqual(comanda['estado'], 'pendiente')
            self.assertEqual(len(comanda['detalles']), 2)
            self.assertEqual(comanda['detalles'][0]['cantidad'], 2)
            self.assertEqual(comanda['detalles'][0]['especificaciones'], 'Sin cebolla')
            self.assertEqual(comanda['detalles'][1]['cantidad'], 1)

    # -------------------------------------------------------------------------
    # CASO 2 — Comanda vacía
    # -------------------------------------------------------------------------
    def test_caso_2_comanda_vacia(self):
        """
        Se intenta registrar una comanda sin productos.
        Resultado esperado: el sistema rechaza la operación con ComandaValidacionError.
        """
        with self.app.app_context():
            db = get_db()
            with self.assertRaises(ComandaValidacionError) as ctx:
                crear_comanda(db, [])
            self.assertIn("al menos un producto", str(ctx.exception).lower())

        # Validación vía endpoint HTTP
        response = self.client.post('/comandas/nueva', data={
            'producto_id[]': [],
            'cantidad[]': [],
            'especificaciones[]': []
        })
        self.assertEqual(response.status_code, 400)

    # -------------------------------------------------------------------------
    # CASO 3 — Cantidad inválida
    # -------------------------------------------------------------------------
    def test_caso_3_cantidad_invalida(self):
        """
        Se intenta agregar un producto con cantidad cero o negativa.
        Resultado esperado: el sistema rechaza la operación con ComandaValidacionError.
        """
        with self.app.app_context():
            db = get_db()
            # Cantidad cero
            with self.assertRaises(ComandaValidacionError):
                crear_comanda(db, [{'producto_id': 1, 'cantidad': 0, 'especificaciones': ''}])

            # Cantidad negativa
            with self.assertRaises(ComandaValidacionError):
                crear_comanda(db, [{'producto_id': 1, 'cantidad': -3, 'especificaciones': ''}])

            # Cantidad no numérica
            with self.assertRaises(ComandaValidacionError):
                crear_comanda(db, [{'producto_id': 1, 'cantidad': 'abc', 'especificaciones': ''}])

        # Validación vía endpoint HTTP con cantidad 0
        response = self.client.post('/comandas/nueva', data={
            'producto_id[]': ['1'],
            'cantidad[]': ['0'],
            'especificaciones[]': ['']
        })
        self.assertEqual(response.status_code, 400)

    # -------------------------------------------------------------------------
    # CASO 4 — Consultar comanda
    # -------------------------------------------------------------------------
    def test_caso_4_consultar_comanda(self):
        """
        Se consulta una comanda existente.
        Resultado esperado: se muestran sus productos, cantidades y especificaciones.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 3, 'especificaciones': 'Carne bien cocida'}
            ])

        response = self.client.get(f'/comandas/{comanda_id}')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn(f"Comanda #{comanda_id}", html)
        self.assertIn("[TEST] Hamburguesa", html)
        self.assertIn("3", html)
        self.assertIn("Carne bien cocida", html)
        self.assertIn("Pendiente", html)

    # -------------------------------------------------------------------------
    # CASO 5 — Modificar comanda pendiente
    # -------------------------------------------------------------------------
    def test_caso_5_modificar_comanda_pendiente(self):
        """
        Se cambia la cantidad o especificación de un producto en comanda pendiente.
        Resultado esperado: la modificación se guarda correctamente.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 1, 'especificaciones': 'Original'}
            ])

            # Modificar aumentando cantidad y agregando un segundo producto
            nuevos_items = [
                {'producto_id': 1, 'cantidad': 4, 'especificaciones': 'Modificado con extra queso'},
                {'producto_id': 2, 'cantidad': 2, 'especificaciones': 'Papas grandes'}
            ]
            resultado = modificar_comanda(db, comanda_id, nuevos_items)
            self.assertTrue(resultado)

            comanda_mod = obtener_detalle_comanda(db, comanda_id)
            self.assertEqual(len(comanda_mod['detalles']), 2)
            self.assertEqual(comanda_mod['detalles'][0]['cantidad'], 4)
            self.assertEqual(comanda_mod['detalles'][0]['especificaciones'], 'Modificado con extra queso')
            self.assertEqual(comanda_mod['detalles'][1]['cantidad'], 2)

    # -------------------------------------------------------------------------
    # CASO 6 — Modificar comanda no pendiente
    # -------------------------------------------------------------------------
    def test_caso_6_modificar_comanda_no_pendiente(self):
        """
        Se intenta modificar una comanda en preparación, finalizada o cancelada.
        Resultado esperado: operación rechazada con ComandaEstadoInvalidoError.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            for estado_bloqueado in ['en preparación', 'finalizada', 'cancelada']:
                db.execute("UPDATE comanda SET estado = ? WHERE comanda_id = ?;", (estado_bloqueado, comanda_id))
                db.commit()

                with self.assertRaises(ComandaEstadoInvalidoError):
                    modificar_comanda(db, comanda_id, [{'producto_id': 2, 'cantidad': 1}])

    # -------------------------------------------------------------------------
    # CASO 7 — Cancelar comanda pendiente
    # -------------------------------------------------------------------------
    def test_caso_7_cancelar_comanda_pendiente(self):
        """
        Se cancela una comanda pendiente.
        Resultado esperado: cambia a estado 'cancelada' y conserva sus registros en SQLite.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Para llevar'}
            ])

            resultado = cancelar_comanda(db, comanda_id)
            self.assertTrue(resultado)

            comanda = obtener_detalle_comanda(db, comanda_id)
            self.assertEqual(comanda['estado'], 'cancelada')
            # Conserva los detalles en base de datos
            self.assertEqual(len(comanda['detalles']), 1)
            self.assertEqual(comanda['detalles'][0]['especificaciones'], 'Para llevar')

    # -------------------------------------------------------------------------
    # CASO 8 — Cancelar comanda no pendiente
    # -------------------------------------------------------------------------
    def test_caso_8_cancelar_comanda_no_pendiente(self):
        """
        Se intenta cancelar una comanda en preparación, finalizada o ya cancelada.
        Resultado esperado: operación rechazada con ComandaEstadoInvalidoError.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            for estado_bloqueado in ['en preparación', 'finalizada', 'cancelada']:
                db.execute("UPDATE comanda SET estado = ? WHERE comanda_id = ?;", (estado_bloqueado, comanda_id))
                db.commit()

                with self.assertRaises(ComandaEstadoInvalidoError):
                    cancelar_comanda(db, comanda_id)

    # -------------------------------------------------------------------------
    # CASO 9 — Integridad referencial
    # -------------------------------------------------------------------------
    def test_caso_9_integridad_referencial_producto_inexistente(self):
        """
        Se intenta guardar un detalle con un producto inexistente.
        Resultado esperado: operación rechazada con ComandaValidacionError.
        """
        with self.app.app_context():
            db = get_db()
            id_inexistente = 99999

            with self.assertRaises(ComandaValidacionError) as ctx:
                crear_comanda(db, [{'producto_id': id_inexistente, 'cantidad': 1}])
            self.assertIn("no existe", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # CASO 10 — Persistencia en SQLite
    # -------------------------------------------------------------------------
    def test_caso_10_persistencia_sqlite(self):
        """
        Se guarda una comanda y se consulta abriendo una conexión nueva independiente.
        Resultado esperado: los datos permanecen almacenados en el archivo SQLite.
        """
        with self.app.app_context():
            db = get_db()
            comanda_id = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 3, 'especificaciones': 'Persistencia comprobada'}
            ])

        # Abrir una conexión nativa directa de sqlite3 al archivo físico
        con_directa = sqlite3.connect(self.db_path)
        cur = con_directa.cursor()

        cur.execute("SELECT comanda_id, estado FROM comanda WHERE comanda_id = ?;", (comanda_id,))
        fila_comanda = cur.fetchone()
        self.assertIsNotNone(fila_comanda)
        self.assertEqual(fila_comanda[0], comanda_id)
        self.assertEqual(fila_comanda[1], 'pendiente')

        cur.execute(
            "SELECT producto_id, cantidad, especificaciones FROM detalle_comanda WHERE comanda_id = ?;",
            (comanda_id,)
        )
        fila_detalle = cur.fetchone()
        self.assertIsNotNone(fila_detalle)
        self.assertEqual(fila_detalle[0], 1)
        self.assertEqual(fila_detalle[1], 3)
        self.assertEqual(fila_detalle[2], 'Persistencia comprobada')

        con_directa.close()

    # -------------------------------------------------------------------------
    # EXTRA — Rechazo de productos inactivos
    # -------------------------------------------------------------------------
    def test_rechazo_producto_inactivo(self):
        """
        Verifica que no se permita agregar productos inactivos a una comanda.
        """
        with self.app.app_context():
            db = get_db()
            # El producto 3 está inactivo
            with self.assertRaises(ComandaValidacionError) as ctx:
                crear_comanda(db, [{'producto_id': 3, 'cantidad': 1}])
            self.assertIn("inactivo", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # PRUEBAS DE ATOMICIDAD Y TRANSACCIONES
    # -------------------------------------------------------------------------
    def test_atomicidad_creacion_falla_detalle(self):
        """
        Verifica que la creación sea estrictamente atómica:
        Si la inserción de un detalle falla, la comanda completa debe revertirse
        mediante rollback, sin dejar registros huérfanos o incompletos.
        """
        from unittest.mock import patch
        from app.modules.comandas.service import ComandaServiceError

        with self.app.app_context():
            db = get_db()
            with patch('app.modules.comandas.repository.insertar_detalle') as mock_det:
                mock_det.side_effect = Exception("Fallo forzado en inserción de detalle")

                with self.assertRaises(ComandaServiceError):
                    crear_comanda(db, [
                        {'producto_id': 1, 'cantidad': 1},
                        {'producto_id': 2, 'cantidad': 1}
                    ])

            # Comprobar que NO quedó registrada ninguna comanda en la tabla
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM comanda;")
            total_comandas = cursor.fetchone()[0]
            self.assertEqual(total_comandas, 0, "No debe persistir ninguna comanda si falló un detalle.")

            cursor.execute("SELECT COUNT(*) FROM detalle_comanda;")
            total_detalles = cursor.fetchone()[0]
            self.assertEqual(total_detalles, 0, "No debe persistir ningún detalle si hubo rollback.")

    def test_atomicidad_modificacion_falla_detalle(self):
        """
        Verifica que la modificación sea estrictamente atómica:
        Si falla la inserción de nuevos detalles, los detalles originales
        deben ser restaurados íntegramente mediante rollback.
        """
        from unittest.mock import patch
        from app.modules.comandas.service import ComandaServiceError

        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Detalle Original'}
            ])

            with patch('app.modules.comandas.repository.insertar_detalle') as mock_det:
                mock_det.side_effect = Exception("Error forzado al insertar nuevos detalles")

                with self.assertRaises(ComandaServiceError):
                    modificar_comanda(db, cid, [
                        {'producto_id': 2, 'cantidad': 5, 'especificaciones': 'Nuevo'}
                    ])

            # Verificar que los detalles originales permanecen intactos
            detalles = db.execute(
                "SELECT producto_id, cantidad, especificaciones FROM detalle_comanda WHERE comanda_id = ?;",
                (cid,)
            ).fetchall()

            self.assertEqual(len(detalles), 1, "Debe conservar exactamente el detalle original.")
            self.assertEqual(detalles[0]['producto_id'], 1)
            self.assertEqual(detalles[0]['cantidad'], 2)
            self.assertEqual(detalles[0]['especificaciones'], 'Detalle Original')

    def test_modificar_comanda_sin_productos_rechazada(self):
        """
        Verifica que modificar una comanda con lista vacía sea rechazado
        y que la comanda nunca pueda quedarse sin productos.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            with self.assertRaises(ComandaValidacionError) as ctx:
                modificar_comanda(db, cid, [])
            self.assertIn("al menos un producto", str(ctx.exception).lower())

            # Verificar que sigue teniendo su producto original
            detalles = db.execute("SELECT COUNT(*) FROM detalle_comanda WHERE comanda_id = ?;", (cid,)).fetchone()[0]
            self.assertEqual(detalles, 1, "La comanda debe conservar su producto original.")

if __name__ == '__main__':
    unittest.main()
