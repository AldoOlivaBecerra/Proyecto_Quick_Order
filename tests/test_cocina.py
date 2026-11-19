"""
Pruebas Automatizadas para el Módulo de Cocina (Kitchen Display System - KDS).
Cubre:
- Consulta de órdenes activas (FIFO, exclusión de canceladas y finalizadas).
- Transición correcta: pendiente -> en preparación.
- Transición correcta: en preparación -> finalizada.
- Rechazo de finalización directa desde pendiente.
- Rechazo de operaciones sobre comandas canceladas o previamente finalizadas.
- Rechazo sobre comanda inexistente (404).
- Verificación del endpoint JSON de Short Polling (/cocina/api/activas).
- Endpoints de transición asíncrona.
- Protección transaccional y ante operaciones simultáneas.
- Integración completa entre Caja y Cocina.
"""
import os
import tempfile
import unittest
from app import create_app
from app.database import get_db, init_db
from app.modules.comandas.service import (
    crear_comanda,
    modificar_comanda,
    cancelar_comanda,
    ComandaEstadoInvalidoError
)
from app.modules.cocina.service import (
    obtener_comandas_cocina,
    iniciar_preparacion,
    finalizar_preparacion,
    CocinaServiceError,
    CocinaComandaNoEncontradaError,
    CocinaTransicionInvalidaError,
    CocinaConcurrenciaError
)

class TestModuloCocina(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el Monitor de Cocina."""

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
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (1, '[TEST] Hamburguesa Doble', 'Con queso', 1);"
            )
            cursor.execute(
                "INSERT INTO producto (producto_id, nombre, descripcion, activo) VALUES (2, '[TEST] Papas Supremas', 'Crujientes', 1);"
            )
            db.commit()

    def tearDown(self):
        """Limpia la base de datos temporal."""
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # 1. Consulta de comandas activas y orden FIFO
    # -------------------------------------------------------------------------
    def test_consulta_comandas_activas_orden_fifo(self):
        """
        Verifica que Cocina consulte únicamente comandas 'pendiente' y 'en preparación'
        ordenadas cronológicamente por FIFO, excluyendo finalizadas y canceladas.
        """
        with self.app.app_context():
            db = get_db()

            # Comanda 1: pendiente (primera en crearse)
            c1 = crear_comanda(db, [{'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Sin cebolla'}])
            
            # Comanda 2: en preparación (segunda en crearse)
            c2 = crear_comanda(db, [{'producto_id': 2, 'cantidad': 1, 'especificaciones': 'Extra salsa'}])
            db.execute("UPDATE comanda SET estado = 'en preparación' WHERE comanda_id = ?;", (c2,))
            
            # Comanda 3: finalizada (debe excluirse de cocina)
            c3 = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])
            db.execute("UPDATE comanda SET estado = 'finalizada' WHERE comanda_id = ?;", (c3,))
            
            # Comanda 4: cancelada (debe excluirse de cocina)
            c4 = crear_comanda(db, [{'producto_id': 2, 'cantidad': 1}])
            db.execute("UPDATE comanda SET estado = 'cancelada' WHERE comanda_id = ?;", (c4,))
            db.commit()

            datos = obtener_comandas_cocina(db)

            # Debe retornar solo 2 comandas activas
            self.assertEqual(datos['total'], 2)
            self.assertEqual(len(datos['pendientes']), 1)
            self.assertEqual(len(datos['en_preparacion']), 1)

            # Verificar orden FIFO (c1 antes de c2)
            ids_activos = [c['comanda_id'] for c in datos['comandas']]
            self.assertEqual(ids_activos, [c1, c2])

            # Verificar detalles de la comanda 1
            comanda_1 = datos['pendientes'][0]
            self.assertEqual(comanda_1['comanda_id'], c1)
            self.assertEqual(comanda_1['estado'], 'pendiente')
            self.assertEqual(len(comanda_1['items']), 1)
            self.assertEqual(comanda_1['items'][0]['producto_nombre'], '[TEST] Hamburguesa Doble')
            self.assertEqual(comanda_1['items'][0]['cantidad'], 2)
            self.assertEqual(comanda_1['items'][0]['especificaciones'], 'Sin cebolla')

    # -------------------------------------------------------------------------
    # 2. Iniciar preparación: pendiente -> en preparación
    # -------------------------------------------------------------------------
    def test_iniciar_preparacion_exitoso(self):
        """
        Verifica la transición exitosa de 'pendiente' a 'en preparación'
        y la actualización del timestamp.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            resultado = iniciar_preparacion(db, cid)
            self.assertTrue(resultado)

            # Comprobar estado en base de datos
            fila = db.execute("SELECT estado, fecha_hora_actualizacion FROM comanda WHERE comanda_id = ?;", (cid,)).fetchone()
            self.assertEqual(fila['estado'], 'en preparación')
            self.assertIsNotNone(fila['fecha_hora_actualizacion'])

    # -------------------------------------------------------------------------
    # 3. Finalizar preparación: en preparación -> finalizada
    # -------------------------------------------------------------------------
    def test_finalizar_preparacion_exitoso(self):
        """
        Verifica la transición de 'en preparación' a 'finalizada'
        y su remoción del monitor activo conservando los registros en SQLite.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Bien cocida'}])
            iniciar_preparacion(db, cid)

            resultado = finalizar_preparacion(db, cid)
            self.assertTrue(resultado)

            # Ya no debe aparecer como orden activa de cocina
            datos = obtener_comandas_cocina(db)
            ids_activos = [c['comanda_id'] for c in datos['comandas']]
            self.assertNotIn(cid, ids_activos)

            # Pero debe permanecer en SQLite con sus detalles intactos
            fila_comanda = db.execute("SELECT estado FROM comanda WHERE comanda_id = ?;", (cid,)).fetchone()
            self.assertEqual(fila_comanda['estado'], 'finalizada')

            detalles = db.execute("SELECT COUNT(*) FROM detalle_comanda WHERE comanda_id = ?;", (cid,)).fetchone()[0]
            self.assertEqual(detalles, 1)

    # -------------------------------------------------------------------------
    # 4. Rechazo de salto directo: pendiente -> finalizada
    # -------------------------------------------------------------------------
    def test_rechazo_finalizar_directamente_desde_pendiente(self):
        """
        Una comanda pendiente NO puede finalizarse sin haber iniciado su preparación.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            with self.assertRaises(CocinaTransicionInvalidaError) as ctx:
                finalizar_preparacion(db, cid)
            self.assertIn("todavía está pendiente", str(ctx.exception).lower())

            # El estado debe continuar siendo 'pendiente'
            estado = db.execute("SELECT estado FROM comanda WHERE comanda_id = ?;", (cid,)).fetchone()['estado']
            self.assertEqual(estado, 'pendiente')

    # -------------------------------------------------------------------------
    # 5. Rechazo de acciones sobre comanda cancelada
    # -------------------------------------------------------------------------
    def test_rechazo_acciones_sobre_comanda_cancelada(self):
        """
        Verifica que no se pueda iniciar ni finalizar una comanda cancelada.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])
            cancelar_comanda(db, cid)

            # Intentar iniciar
            with self.assertRaises(CocinaTransicionInvalidaError) as ctx_iniciar:
                iniciar_preparacion(db, cid)
            self.assertIn("cancelada", str(ctx_iniciar.exception).lower())

            # Intentar finalizar
            with self.assertRaises(CocinaTransicionInvalidaError) as ctx_fin:
                finalizar_preparacion(db, cid)
            self.assertIn("cancelada", str(ctx_fin.exception).lower())

    # -------------------------------------------------------------------------
    # 6. Rechazo de acciones sobre comanda finalizada
    # -------------------------------------------------------------------------
    def test_rechazo_acciones_sobre_comanda_finalizada(self):
        """
        Verifica que una orden ya finalizada no admita reinicios ni finalizaciones redundantes.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])
            iniciar_preparacion(db, cid)
            finalizar_preparacion(db, cid)

            # Intentar iniciar comanda ya finalizada
            with self.assertRaises(CocinaTransicionInvalidaError):
                iniciar_preparacion(db, cid)

            # Intentar finalizar comanda ya finalizada
            with self.assertRaises(CocinaTransicionInvalidaError):
                finalizar_preparacion(db, cid)

    # -------------------------------------------------------------------------
    # 7. Rechazo sobre comanda inexistente (404)
    # -------------------------------------------------------------------------
    def test_comanda_inexistente(self):
        """
        Verifica que consultar o alterar una comanda inexistente lance CocinaComandaNoEncontradaError.
        """
        with self.app.app_context():
            db = get_db()
            id_falso = 88888

            with self.assertRaises(CocinaComandaNoEncontradaError):
                iniciar_preparacion(db, id_falso)

            with self.assertRaises(CocinaComandaNoEncontradaError):
                finalizar_preparacion(db, id_falso)

    # -------------------------------------------------------------------------
    # 8. Endpoint API JSON para Short Polling (/cocina/api/activas)
    # -------------------------------------------------------------------------
    def test_endpoint_api_activas_polling(self):
        """
        Verifica que el endpoint JSON retorne HTTP 200 con la estructura requerida
        para el mecanismo de actualización cada 1.5s.
        """
        with self.app.app_context():
            db = get_db()
            crear_comanda(db, [{'producto_id': 1, 'cantidad': 3, 'especificaciones': 'Para llevar'}])

        response = self.client.get('/cocina/api/activas')
        self.assertEqual(response.status_code, 200)

        json_data = response.get_json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['total'], 1)
        self.assertEqual(len(json_data['pendientes']), 1)
        self.assertEqual(len(json_data['en_preparacion']), 0)
        self.assertIn('timestamp', json_data)
        self.assertEqual(json_data['pendientes'][0]['items'][0]['especificaciones'], 'Para llevar')

    # -------------------------------------------------------------------------
    # 9. Endpoints API de transición asíncrona
    # -------------------------------------------------------------------------
    def test_endpoints_api_transiciones_json(self):
        """
        Verifica el funcionamiento de los endpoints POST de transición asíncrona.
        """
        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

        # 1. POST para iniciar preparación
        resp_iniciar = self.client.post(f'/cocina/api/comandas/{cid}/iniciar')
        self.assertEqual(resp_iniciar.status_code, 200)
        data_ini = resp_iniciar.get_json()
        self.assertTrue(data_ini['success'])
        self.assertEqual(data_ini['nuevo_estado'], 'en preparación')

        # 2. POST para finalizar preparación
        resp_fin = self.client.post(f'/cocina/api/comandas/{cid}/finalizar')
        self.assertEqual(resp_fin.status_code, 200)
        data_fin = resp_fin.get_json()
        self.assertTrue(data_fin['success'])
        self.assertEqual(data_fin['nuevo_estado'], 'finalizada')

    # -------------------------------------------------------------------------
    # 10. Protección ante concurrencia / operaciones simultáneas
    # -------------------------------------------------------------------------
    def test_proteccion_concurrencia_cambio_simultaneo(self):
        """
        Verifica que si el estado de la comanda cambia simultáneamente en la base
        de datos, la actualización atómica falle de forma controlada con CocinaConcurrenciaError.
        """
        from unittest.mock import patch

        with self.app.app_context():
            db = get_db()
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 1}])

            # Simular que repository.actualizar_estado_comanda no actualizó registros
            # porque otra transacción modificó el estado_esperado
            with patch('app.modules.cocina.repository.actualizar_estado_comanda', return_value=False):
                with self.assertRaises(CocinaConcurrenciaError) as ctx:
                    iniciar_preparacion(db, cid)
                self.assertIn("modificada simultáneamente", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # 11. Integración de extremo a extremo: Caja -> Cocina
    # -------------------------------------------------------------------------
    def test_integracion_caja_y_cocina(self):
        """
        Flujo completo:
        1. Cajero registra comanda en Caja (estado 'pendiente').
        2. Cocina detecta la orden pendiente.
        3. Cocina inicia la preparación ('en preparación').
        4. Cajero intenta modificar o cancelar la orden -> Rechazado por reglas de negocio.
        5. Cocina finaliza la preparación ('finalizada').
        6. La comanda desaparece del monitor activo de Cocina pero permanece archivada en SQLite.
        """
        with self.app.app_context():
            db = get_db()

            # 1. Cajero crea comanda
            cid = crear_comanda(db, [{'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Mesa 4'}])

            # 2. Cocina la visualiza
            datos_cocina = obtener_comandas_cocina(db)
            self.assertEqual(datos_cocina['total'], 1)
            self.assertEqual(datos_cocina['pendientes'][0]['comanda_id'], cid)

            # 3. Cocina inicia preparación
            iniciar_preparacion(db, cid)

            # 4. Cajero intenta cancelarla o modificarla
            with self.assertRaises(ComandaEstadoInvalidoError):
                cancelar_comanda(db, cid)

            with self.assertRaises(ComandaEstadoInvalidoError):
                modificar_comanda(db, cid, [{'producto_id': 2, 'cantidad': 1}])

            # 5. Cocina finaliza
            finalizar_preparacion(db, cid)

            # 6. Desaparece de cocina activa pero persiste en BD
            datos_finales = obtener_comandas_cocina(db)
            self.assertEqual(datos_finales['total'], 0)

            estado_db = db.execute("SELECT estado FROM comanda WHERE comanda_id = ?;", (cid,)).fetchone()['estado']
            self.assertEqual(estado_db, 'finalizada')

    # -------------------------------------------------------------------------
    # 12. Renderizado de plantilla HTML de Cocina (GET /cocina/)
    # -------------------------------------------------------------------------
    def test_renderizado_pantalla_cocina_con_productos(self):
        """
        Verifica que GET /cocina devuelva HTTP 200 y renderice sin errores
        la plantilla Jinja2 cuando existen comandas con productos asociados,
        mostrando nombres, cantidades y especificaciones correctamente.
        """
        with self.app.app_context():
            db = get_db()
            c_pen = crear_comanda(db, [
                {'producto_id': 1, 'cantidad': 2, 'especificaciones': 'Sin cebolla'}
            ])
            c_prep = crear_comanda(db, [
                {'producto_id': 2, 'cantidad': 3, 'especificaciones': 'Extra sal'}
            ])
            iniciar_preparacion(db, c_prep)

        response = self.client.get('/cocina/')
        self.assertEqual(response.status_code, 200, "GET /cocina/ debe devolver HTTP 200.")
        html = response.get_data(as_text=True)

        # Verificar encabezados y secciones
        self.assertIn("Monitor de Cocina (KDS)", html)
        self.assertIn("Por Preparar (Pendientes)", html)
        self.assertIn("En Preparación (En Curso)", html)

        # Verificar presencia de ambas comandas
        self.assertIn(f"#{c_pen}", html)
        self.assertIn(f"#{c_prep}", html)

        # Verificar productos, cantidades y especificaciones
        self.assertIn("[TEST] Hamburguesa Doble", html)
        self.assertIn("2x", html)
        self.assertIn("Sin cebolla", html)

        self.assertIn("[TEST] Papas Supremas", html)
        self.assertIn("3x", html)
        self.assertIn("Extra sal", html)

if __name__ == '__main__':
    unittest.main()
