"""
Controlador y Rutas del módulo de Comandas.
Gestiona las peticiones HTTP para:
- Crear una nueva comanda con productos activos.
- Consultar el listado general y detalle completo de comandas.
- Modificar comandas pendientes.
- Cancelar comandas pendientes.
Se comunica exclusivamente con la capa de servicio (service.py) y con el servicio de productos.
"""
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, jsonify
)
from app.database import get_db
from app.modules.productos.service import (
    obtener_catalogo_productos,
    ProductoServiceError
)
from app.modules.comandas.service import (
    crear_comanda,
    obtener_comandas,
    obtener_detalle_comanda,
    modificar_comanda,
    cancelar_comanda,
    ComandaServiceError,
    ComandaNoEncontradaError,
    ComandaEstadoInvalidoError,
    ComandaValidacionError
)

comandas_bp = Blueprint('comandas', __name__, url_prefix='/comandas')

def _parsear_items_formulario(form_data):
    """
    Auxiliar para extraer listas de productos, cantidades y especificaciones
    desde formularios HTML estándar (POST) o payloads JSON.
    """
    items = []
    
    if request.is_json:
        json_data = request.get_json() or {}
        return json_data.get('items', [])

    # Procesar listas desde formulario HTML
    p_ids = form_data.getlist('producto_id[]')
    cants = form_data.getlist('cantidad[]')
    specs = form_data.getlist('especificaciones[]')

    for i in range(len(p_ids)):
        p_id = p_ids[i].strip() if p_ids[i] else ''
        if not p_id:
            continue
        cant = cants[i].strip() if i < len(cants) and cants[i] else '1'
        spec = specs[i].strip() if i < len(specs) and specs[i] else ''
        items.append({
            'producto_id': p_id,
            'cantidad': cant,
            'especificaciones': spec
        })

    return items

@comandas_bp.route('/', methods=['GET'])
def listar_comandas():
    """
    Pantalla principal de comandas: muestra la lista de todas las comandas registradas.
    """
    error_mensaje = None
    comandas = []
    status_code = 200

    try:
        db = get_db()
        comandas = obtener_comandas(db)
    except ComandaServiceError as err:
        current_app.logger.error("Error al obtener listado de comandas: %s", err)
        error_mensaje = "No fue posible consultar las comandas. Intente más tarde."
        status_code = 500
    except Exception as exc:
        current_app.logger.exception("Error inesperado al listar comandas: %s", exc)
        error_mensaje = "Ocurrió un error inesperado al procesar las comandas."
        status_code = 500

    return render_template(
        'comandas/lista.html',
        comandas=comandas,
        error_mensaje=error_mensaje
    ), status_code

@comandas_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_comanda():
    """
    GET: Muestra la pantalla para crear una comanda con el selector de productos activos.
    POST: Procesa el registro de la nueva comanda.
    """
    db = get_db()

    # Obtener catálogo de productos activos para el selector
    productos_activos = []
    try:
        productos_activos = obtener_catalogo_productos(db)
    except ProductoServiceError as err:
        current_app.logger.error("Error al cargar productos para comanda: %s", err)
        flash("No se pudieron cargar los productos disponibles para ordenar.", "error")

    if request.method == 'POST':
        items = _parsear_items_formulario(request.form)

        try:
            comanda_id = crear_comanda(db, items)
            flash(f"¡Comanda #{comanda_id} registrada exitosamente!", "success")
            return redirect(url_for('comandas.ver_comanda', comanda_id=comanda_id))
        except ComandaValidacionError as val_err:
            flash(str(val_err), "error")
            return render_template(
                'comandas/crear.html',
                productos_activos=productos_activos,
                items_previos=items
            ), 400
        except ComandaServiceError as serv_err:
            current_app.logger.error("Error de servicio al crear comanda: %s", serv_err)
            flash("Error interno al registrar la comanda. Intente de nuevo.", "error")
            return render_template(
                'comandas/crear.html',
                productos_activos=productos_activos,
                items_previos=items
            ), 500

    return render_template(
        'comandas/crear.html',
        productos_activos=productos_activos,
        items_previos=[]
    )

@comandas_bp.route('/<int:comanda_id>', methods=['GET'])
def ver_comanda(comanda_id):
    """
    Muestra la vista de detalle completo de una comanda específica.
    """
    db = get_db()
    try:
        comanda = obtener_detalle_comanda(db, comanda_id)
        return render_template('comandas/detalle.html', comanda=comanda)
    except ComandaNoEncontradaError:
        flash(f"La comanda #{comanda_id} no fue encontrada.", "error")
        return redirect(url_for('comandas.listar_comandas')), 404
    except ComandaServiceError as err:
        current_app.logger.error("Error al consultar comanda #%s: %s", comanda_id, err)
        flash("Ocurrió un error al consultar el detalle de la comanda.", "error")
        return redirect(url_for('comandas.listar_comandas')), 500

@comandas_bp.route('/<int:comanda_id>/editar', methods=['GET', 'POST'])
def editar_comanda(comanda_id):
    """
    GET: Muestra la pantalla para modificar una comanda (solo si su estado es 'pendiente').
    POST: Procesa las modificaciones de la comanda.
    """
    db = get_db()

    # Verificar existencia y estado de la comanda
    try:
        comanda = obtener_detalle_comanda(db, comanda_id)
    except ComandaNoEncontradaError:
        flash(f"La comanda #{comanda_id} no existe.", "error")
        return redirect(url_for('comandas.listar_comandas')), 404
    except ComandaServiceError:
        flash("Error al acceder a la comanda para edición.", "error")
        return redirect(url_for('comandas.listar_comandas')), 500

    if comanda['estado'] != 'pendiente':
        flash(
            f"No es posible modificar la comanda #{comanda_id} porque su estado es '{comanda['estado']}'. "
            "Solo se pueden modificar pedidos en estado 'pendiente'.",
            "warning"
        )
        return redirect(url_for('comandas.ver_comanda', comanda_id=comanda_id))

    productos_activos = []
    try:
        productos_activos = obtener_catalogo_productos(db)
    except ProductoServiceError:
        flash("No se pudieron cargar los productos para la modificación.", "error")

    if request.method == 'POST':
        items = _parsear_items_formulario(request.form)

        try:
            modificar_comanda(db, comanda_id, items)
            flash(f"¡Comanda #{comanda_id} modificada exitosamente!", "success")
            return redirect(url_for('comandas.ver_comanda', comanda_id=comanda_id))
        except ComandaEstadoInvalidoError as est_err:
            flash(str(est_err), "warning")
            return redirect(url_for('comandas.ver_comanda', comanda_id=comanda_id))
        except ComandaValidacionError as val_err:
            flash(str(val_err), "error")
            return render_template(
                'comandas/editar.html',
                comanda=comanda,
                productos_activos=productos_activos,
                items_previos=items
            ), 400
        except ComandaServiceError as serv_err:
            current_app.logger.error("Error al modificar comanda #%s: %s", comanda_id, serv_err)
            flash("Error interno al modificar la comanda.", "error")
            return render_template(
                'comandas/editar.html',
                comanda=comanda,
                productos_activos=productos_activos,
                items_previos=items
            ), 500

    return render_template(
        'comandas/editar.html',
        comanda=comanda,
        productos_activos=productos_activos,
        items_previos=[]
    )

@comandas_bp.route('/<int:comanda_id>/cancelar', methods=['POST'])
def cancelar_comanda_accion(comanda_id):
    """
    Acción para cancelar una comanda pendiente.
    Solo admite método POST para evitar cancelaciones involuntarias.
    """
    db = get_db()
    try:
        cancelar_comanda(db, comanda_id)
        flash(f"La comanda #{comanda_id} ha sido cancelada correctamente.", "success")
    except ComandaNoEncontradaError:
        flash(f"No se encontró la comanda #{comanda_id} para cancelar.", "error")
    except ComandaEstadoInvalidoError as est_err:
        flash(str(est_err), "warning")
    except ComandaServiceError as err:
        current_app.logger.error("Error al cancelar comanda #%s: %s", comanda_id, err)
        flash("Ocurrió un error al intentar cancelar la comanda.", "error")

    return redirect(url_for('comandas.ver_comanda', comanda_id=comanda_id))
