"""
Controlador y Rutas del módulo de Cocina (Kitchen Display System - KDS).
Gestiona:
- Pantalla visual de cocina (tablero Kanban de pedidos activos).
- Endpoint JSON optimizado para actualización automática cada 1.5s (Short Polling).
- Endpoints de transición: Iniciar preparación y Finalizar preparación.
"""
from datetime import datetime, timezone
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, current_app
from app.database import get_db
from app.modules.cocina.service import (
    obtener_comandas_cocina,
    iniciar_preparacion,
    finalizar_preparacion,
    CocinaServiceError,
    CocinaComandaNoEncontradaError,
    CocinaTransicionInvalidaError,
    CocinaConcurrenciaError
)

cocina_bp = Blueprint('cocina', __name__, url_prefix='/cocina')

@cocina_bp.route('/', methods=['GET'])
def pantalla_cocina():
    """
    Pantalla principal del monitor de cocina (KDS).
    Carga el estado inicial de pedidos pendientes y en preparación.
    """
    db = get_db()
    datos_cocina = {'pendientes': [], 'en_preparacion': [], 'total': 0}
    error_mensaje = None

    try:
        datos_cocina = obtener_comandas_cocina(db)
    except CocinaServiceError as err:
        current_app.logger.error("Error al cargar pantalla de cocina: %s", err)
        error_mensaje = "No fue posible conectar con el servidor para cargar las órdenes de cocina."

    return render_template(
        'cocina/pantalla.html',
        pendientes=datos_cocina['pendientes'],
        en_preparacion=datos_cocina['en_preparacion'],
        total=datos_cocina['total'],
        error_mensaje=error_mensaje
    )

@cocina_bp.route('/api/activas', methods=['GET'])
def api_comandas_activas():
    """
    Endpoint JSON ligero para el mecanismo de actualización periódica (polling cada 1.5s).
    Retorna la lista de pedidos pendientes y en preparación.
    """
    db = get_db()
    try:
        datos = obtener_comandas_cocina(db)
        return jsonify({
            'success': True,
            'total': datos['total'],
            'pendientes': datos['pendientes'],
            'en_preparacion': datos['en_preparacion'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    except CocinaServiceError as err:
        current_app.logger.error("Error en polling de cocina: %s", err)
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500

@cocina_bp.route('/api/comandas/<int:comanda_id>/iniciar', methods=['POST'])
def api_iniciar_preparacion(comanda_id):
    """
    Inicia la preparación de una comanda (pendiente -> en preparación).
    Soporta peticiones asíncronas JSON (fetch) y formularios HTML estándar.
    """
    db = get_db()
    is_async = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'api' in request.path

    try:
        iniciar_preparacion(db, comanda_id)
        if is_async:
            return jsonify({
                'success': True,
                'comanda_id': comanda_id,
                'nuevo_estado': 'en preparación',
                'mensaje': f'Comanda #{comanda_id} en preparación.'
            }), 200
        flash(f"Comanda #{comanda_id} en preparación.", "success")
        return redirect(url_for('cocina.pantalla_cocina'))

    except CocinaComandaNoEncontradaError as err:
        if is_async:
            return jsonify({'success': False, 'error': str(err)}), 404
        flash(str(err), "error")
        return redirect(url_for('cocina.pantalla_cocina')), 404

    except (CocinaTransicionInvalidaError, CocinaConcurrenciaError) as err:
        if is_async:
            return jsonify({'success': False, 'error': str(err)}), 400
        flash(str(err), "warning")
        return redirect(url_for('cocina.pantalla_cocina')), 400

    except CocinaServiceError as err:
        current_app.logger.error("Error al iniciar comanda #%s: %s", comanda_id, err)
        if is_async:
            return jsonify({'success': False, 'error': "Error interno del servidor."}), 500
        flash("Error interno al procesar el inicio de la orden.", "error")
        return redirect(url_for('cocina.pantalla_cocina')), 500

@cocina_bp.route('/api/comandas/<int:comanda_id>/finalizar', methods=['POST'])
def api_finalizar_preparacion(comanda_id):
    """
    Finaliza la preparación de una comanda (en preparación -> finalizada).
    Retira la orden del monitor activo manteniéndola archivada en SQLite.
    """
    db = get_db()
    is_async = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'api' in request.path

    try:
        finalizar_preparacion(db, comanda_id)
        if is_async:
            return jsonify({
                'success': True,
                'comanda_id': comanda_id,
                'nuevo_estado': 'finalizada',
                'mensaje': f'Comanda #{comanda_id} finalizada exitosamente.'
            }), 200
        flash(f"Comanda #{comanda_id} finalizada exitosamente.", "success")
        return redirect(url_for('cocina.pantalla_cocina'))

    except CocinaComandaNoEncontradaError as err:
        if is_async:
            return jsonify({'success': False, 'error': str(err)}), 404
        flash(str(err), "error")
        return redirect(url_for('cocina.pantalla_cocina')), 404

    except (CocinaTransicionInvalidaError, CocinaConcurrenciaError) as err:
        if is_async:
            return jsonify({'success': False, 'error': str(err)}), 400
        flash(str(err), "warning")
        return redirect(url_for('cocina.pantalla_cocina')), 400

    except CocinaServiceError as err:
        current_app.logger.error("Error al finalizar comanda #%s: %s", comanda_id, err)
        if is_async:
            return jsonify({'success': False, 'error': "Error interno del servidor."}), 500
        flash("Error interno al finalizar la orden.", "error")
        return redirect(url_for('cocina.pantalla_cocina')), 500
