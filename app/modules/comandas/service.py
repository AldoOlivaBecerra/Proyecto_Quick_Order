"""
Capa de Lógica de Negocio (Service) para el módulo de Comandas.
Coordina y valida las reglas del negocio de comandas:
- Creación, consulta, modificación y cancelación.
- Control estricto de estados ('pendiente', 'en preparación', 'finalizada', 'cancelada').
- Validación de productos activos y cantidades mayores a cero.
- Manejo de transacciones atómicas.
"""
import logging
from app.modules.comandas import repository
from app.modules.comandas.repository import DatabaseError

logger = logging.getLogger(__name__)

ESTADO_PENDIENTE = 'pendiente'
ESTADO_EN_PREPARACION = 'en preparación'
ESTADO_FINALIZADA = 'finalizada'
ESTADO_CANCELADA = 'cancelada'

ESTADOS_VALIDOS = (ESTADO_PENDIENTE, ESTADO_EN_PREPARACION, ESTADO_FINALIZADA, ESTADO_CANCELADA)

class ComandaServiceError(Exception):
    """Excepción base de la capa de servicio de comandas."""
    pass

class ComandaNoEncontradaError(ComandaServiceError):
    """Lanzada cuando no se encuentra la comanda solicitada."""
    pass

class ComandaEstadoInvalidoError(ComandaServiceError):
    """Lanzada cuando se intenta una operación no permitida para el estado actual de la comanda."""
    pass

class ComandaValidacionError(ComandaServiceError):
    """Lanzada cuando los datos de la comanda no cumplen con las reglas de negocio."""
    pass

def _validar_items_comanda(db_conn, items):
    """
    Función interna de validación de los productos que componen una comanda.
    Reglas:
    - Debe contener al menos un producto.
    - La cantidad debe ser un entero mayor a cero.
    - El producto debe existir en la base de datos.
    - Solo se permiten productos activos (activo = 1).
    """
    if not items or len(items) == 0:
        raise ComandaValidacionError("Una comanda debe contener al menos un producto.")

    items_validados = []
    for indice, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ComandaValidacionError(f"El elemento #{indice} tiene un formato inválido.")

        # Validar producto_id
        producto_id = item.get('producto_id')
        try:
            producto_id = int(producto_id)
        except (ValueError, TypeError):
            raise ComandaValidacionError(f"El identificador del producto en la línea #{indice} es inválido.")

        # Validar existencia del producto
        producto = repository.obtener_producto_por_id(db_conn, producto_id)
        if not producto:
            raise ComandaValidacionError(f"El producto con ID {producto_id} no existe en la base de datos.")

        # Validar que el producto esté activo
        if producto.get('activo') != 1:
            nombre_prod = producto.get('nombre', f'ID {producto_id}')
            raise ComandaValidacionError(f"El producto '{nombre_prod}' se encuentra inactivo y no se puede ordenar.")

        # Validar cantidad
        cantidad = item.get('cantidad')
        try:
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            raise ComandaValidacionError(f"La cantidad para '{producto['nombre']}' debe ser un número entero.")

        if cantidad <= 0:
            raise ComandaValidacionError(
                f"La cantidad para '{producto['nombre']}' debe ser un número entero mayor que cero."
            )

        # Especificaciones opcionales
        especificaciones = item.get('especificaciones', '')
        especificaciones = especificaciones.strip() if especificaciones else ''

        items_validados.append({
            'producto_id': producto_id,
            'cantidad': cantidad,
            'especificaciones': especificaciones,
            'producto_nombre': producto['nombre']
        })

    return items_validados

def crear_comanda(db_conn, items):
    """
    Registra una nueva comanda con sus productos correspondientes.
    
    Reglas:
    - Estado inicial: 'pendiente'.
    - Transacción atómica: si falla la inserción de algún detalle, se revierte todo.
    
    Retorna:
        int: Identificador de la comanda creada (comanda_id).
    """
    if db_conn is None:
        raise ComandaServiceError("Conexión a base de datos no disponible.")

    items_validados = _validar_items_comanda(db_conn, items)

    try:
        # Iniciar transacción manual
        comanda_id = repository.insertar_comanda(db_conn, estado=ESTADO_PENDIENTE)

        for item in items_validados:
            repository.insertar_detalle(
                db_conn,
                comanda_id=comanda_id,
                producto_id=item['producto_id'],
                cantidad=item['cantidad'],
                especificaciones=item['especificaciones']
            )

        db_conn.commit()
        logger.info("Comanda #%s creada exitosamente con %s productos.", comanda_id, len(items_validados))
        return comanda_id

    except DatabaseError as err:
        db_conn.rollback()
        logger.error("Error al persistir comanda en la base de datos: %s", err)
        raise ComandaServiceError(f"No fue posible registrar la comanda: {err}") from err
    except Exception as exc:
        db_conn.rollback()
        logger.exception("Error inesperado en servicio al crear comanda: %s", exc)
        raise ComandaServiceError(f"Error inesperado al crear la comanda: {exc}") from exc

def obtener_comandas(db_conn):
    """
    Obtiene el listado general de comandas con sus totales para la pantalla de consulta.
    """
    if db_conn is None:
        raise ComandaServiceError("Conexión a base de datos no disponible.")
    try:
        return repository.obtener_comandas(db_conn)
    except DatabaseError as err:
        logger.error("Error al obtener lista de comandas: %s", err)
        raise ComandaServiceError(f"No fue posible consultar el listado de comandas: {err}") from err

def obtener_detalle_comanda(db_conn, comanda_id):
    """
    Obtiene la información completa de una comanda específica incluyendo todos sus detalles.
    """
    if db_conn is None:
        raise ComandaServiceError("Conexión a base de datos no disponible.")

    try:
        comanda = repository.obtener_comanda_por_id(db_conn, comanda_id)
        if not comanda:
            raise ComandaNoEncontradaError(f"La comanda #{comanda_id} no existe.")

        detalles = repository.obtener_detalles_por_comanda_id(db_conn, comanda_id)
        comanda['detalles'] = detalles
        return comanda

    except (ComandaNoEncontradaError, DatabaseError):
        raise
    except Exception as exc:
        logger.exception("Error inesperado al consultar detalle de comanda #%s: %s", comanda_id, exc)
        raise ComandaServiceError(f"Error al consultar el detalle de la comanda: {exc}") from exc

def modificar_comanda(db_conn, comanda_id, items):
    """
    Modifica los productos, cantidades y especificaciones de una comanda existente.
    
    Reglas:
    - Únicamente se puede modificar si su estado actual es 'pendiente'.
    - Rechaza la modificación si está 'en preparación', 'finalizada' o 'cancelada'.
    - Debe conservar al menos un producto válido.
    - Se ejecuta bajo una transacción atómica.
    - Actualiza fecha_hora_actualizacion.
    """
    if db_conn is None:
        raise ComandaServiceError("Conexión a base de datos no disponible.")

    comanda = repository.obtener_comanda_por_id(db_conn, comanda_id)
    if not comanda:
        raise ComandaNoEncontradaError(f"La comanda #{comanda_id} no existe.")

    # Regla: Solo modificar si está pendiente
    if comanda['estado'] != ESTADO_PENDIENTE:
        raise ComandaEstadoInvalidoError(
            f"No es posible modificar la comanda #{comanda_id} porque se encuentra en estado '{comanda['estado']}'. "
            f"Solo se permite modificar comandas en estado '{ESTADO_PENDIENTE}'."
        )

    items_validados = _validar_items_comanda(db_conn, items)

    try:
        # Reemplazo atómico de detalles
        repository.eliminar_detalles_por_comanda_id(db_conn, comanda_id)

        for item in items_validados:
            repository.insertar_detalle(
                db_conn,
                comanda_id=comanda_id,
                producto_id=item['producto_id'],
                cantidad=item['cantidad'],
                especificaciones=item['especificaciones']
            )

        repository.actualizar_fecha_modificacion(db_conn, comanda_id)
        db_conn.commit()
        logger.info("Comanda #%s modificada exitosamente.", comanda_id)
        return True

    except DatabaseError as err:
        db_conn.rollback()
        logger.error("Error al modificar comanda #%s: %s", comanda_id, err)
        raise ComandaServiceError(f"No fue posible modificar la comanda: {err}") from err
    except Exception as exc:
        db_conn.rollback()
        logger.exception("Error inesperado al modificar comanda #%s: %s", comanda_id, exc)
        raise ComandaServiceError(f"Error inesperado al modificar la comanda: {exc}") from exc

def cancelar_comanda(db_conn, comanda_id):
    """
    Cancela una comanda existente cambiando su estado a 'cancelada'.
    
    Reglas:
    - Únicamente se puede cancelar si su estado actual es 'pendiente'.
    - Rechaza la cancelación si está 'en preparación', 'finalizada' o 'cancelada'.
    - NO elimina físicamente los registros de la base de datos (borrado lógico).
    - Conserva todos los detalles e historial.
    """
    if db_conn is None:
        raise ComandaServiceError("Conexión a base de datos no disponible.")

    comanda = repository.obtener_comanda_por_id(db_conn, comanda_id)
    if not comanda:
        raise ComandaNoEncontradaError(f"La comanda #{comanda_id} no existe.")

    if comanda['estado'] != ESTADO_PENDIENTE:
        raise ComandaEstadoInvalidoError(
            f"No es posible cancelar la comanda #{comanda_id} porque su estado es '{comanda['estado']}'. "
            f"Solo se pueden cancelar comandas en estado '{ESTADO_PENDIENTE}'."
        )

    try:
        repository.actualizar_estado_comanda(db_conn, comanda_id, ESTADO_CANCELADA)
        db_conn.commit()
        logger.info("Comanda #%s cancelada exitosamente.", comanda_id)
        return True
    except DatabaseError as err:
        db_conn.rollback()
        logger.error("Error al cancelar comanda #%s: %s", comanda_id, err)
        raise ComandaServiceError(f"No fue posible cancelar la comanda: {err}") from err
    except Exception as exc:
        db_conn.rollback()
        logger.exception("Error inesperado al cancelar comanda #%s: %s", comanda_id, exc)
        raise ComandaServiceError(f"Error inesperado al cancelar la comanda: {exc}") from exc
