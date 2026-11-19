"""
Capa de Lógica de Negocio (Service) para el módulo de Cocina.
Implementa y valida las reglas de negocio para la preparación de pedidos:
- Control estricto de transiciones:
    * 'pendiente' -> 'en preparación' (Iniciar)
    * 'en preparación' -> 'finalizada' (Finalizar)
- Bloqueo de saltos de estado inválidos (ej. pendiente a finalizada directamente).
- Bloqueo de acciones sobre comandas canceladas o previamente finalizadas.
- Manejo transaccional seguro y protección ante concurrencia.
"""
import logging
from app.modules.cocina import repository
from app.modules.cocina.repository import DatabaseError

logger = logging.getLogger(__name__)

ESTADO_PENDIENTE = 'pendiente'
ESTADO_EN_PREPARACION = 'en preparación'
ESTADO_FINALIZADA = 'finalizada'
ESTADO_CANCELADA = 'cancelada'

class CocinaServiceError(Exception):
    """Excepción base del servicio de cocina."""
    pass

class CocinaComandaNoEncontradaError(CocinaServiceError):
    """Se lanza cuando no se encuentra la comanda solicitada en cocina."""
    pass

class CocinaTransicionInvalidaError(CocinaServiceError):
    """Se lanza cuando se solicita un cambio de estado no permitido."""
    pass

class CocinaConcurrenciaError(CocinaServiceError):
    """Se lanza cuando el estado de la comanda cambió simultáneamente."""
    pass

def obtener_comandas_cocina(db_conn):
    """
    Obtiene las comandas activas para el monitor de cocina (KDS).
    Solo incluye comandas en estado 'pendiente' y 'en preparación' ordenadas por FIFO.
    
    Retorna:
        dict: Diccionario agrupado con listas 'pendientes', 'en_preparacion' y 'total'.
    """
    if db_conn is None:
        raise CocinaServiceError("Conexión a base de datos no disponible.")

    try:
        comandas = repository.obtener_comandas_activas(db_conn)
        
        pendientes = []
        en_preparacion = []

        for c in comandas:
            if c['estado'] == ESTADO_PENDIENTE:
                pendientes.append(c)
            elif c['estado'] == ESTADO_EN_PREPARACION:
                en_preparacion.append(c)

        return {
            'comandas': comandas,
            'pendientes': pendientes,
            'en_preparacion': en_preparacion,
            'total': len(comandas)
        }
    except DatabaseError as err:
        logger.error("Error al obtener comandas para monitor de cocina: %s", err)
        raise CocinaServiceError(f"No fue posible consultar las órdenes de cocina: {err}") from err

def iniciar_preparacion(db_conn, comanda_id):
    """
    Inicia la preparación de una comanda en cocina.
    Transición permitida: 'pendiente' -> 'en preparación'.
    
    Reglas:
    - Solo se permite si la comanda existe y su estado es 'pendiente'.
    - Si ya está 'en preparación', informa que ya está en curso.
    - Rechaza si está 'finalizada' o 'cancelada'.
    - Actualiza atómicamente el estado y la fecha de última modificación.
    """
    if db_conn is None:
        raise CocinaServiceError("Conexión a base de datos no disponible.")

    comanda = repository.obtener_comanda_por_id(db_conn, comanda_id)
    if not comanda:
        raise CocinaComandaNoEncontradaError(f"No se encontró la comanda #{comanda_id}.")

    estado_actual = comanda['estado']

    if estado_actual == ESTADO_CANCELADA:
        raise CocinaTransicionInvalidaError(
            f"No se puede iniciar la comanda #{comanda_id} porque fue cancelada por caja."
        )

    if estado_actual == ESTADO_FINALIZADA:
        raise CocinaTransicionInvalidaError(
            f"No se puede iniciar la comanda #{comanda_id} porque ya fue finalizada."
        )

    if estado_actual == ESTADO_EN_PREPARACION:
        raise CocinaTransicionInvalidaError(
            f"La comanda #{comanda_id} ya se encuentra en preparación."
        )

    if estado_actual != ESTADO_PENDIENTE:
        raise CocinaTransicionInvalidaError(
            f"Transición inválida: no se puede iniciar una comanda en estado '{estado_actual}'."
        )

    try:
        actualizado = repository.actualizar_estado_comanda(
            db_conn,
            comanda_id=comanda_id,
            nuevo_estado=ESTADO_EN_PREPARACION,
            estado_esperado=ESTADO_PENDIENTE
        )

        if not actualizado:
            db_conn.rollback()
            raise CocinaConcurrenciaError(
                f"La comanda #{comanda_id} fue modificada simultáneamente. Por favor actualice el monitor."
            )

        db_conn.commit()
        logger.info("Comanda #%s pasó a 'en preparación' exitosamente.", comanda_id)
        return True

    except DatabaseError as err:
        db_conn.rollback()
        logger.error("Error al iniciar preparación de comanda #%s: %s", comanda_id, err)
        raise CocinaServiceError(f"No fue posible iniciar la preparación: {err}") from err

def finalizar_preparacion(db_conn, comanda_id):
    """
    Marca como finalizada la preparación de una comanda.
    Transición permitida: 'en preparación' -> 'finalizada'.
    
    Reglas:
    - Solo se permite si la comanda existe y su estado es 'en preparación'.
    - No permite finalizar si todavía está 'pendiente' (debe iniciarse primero).
    - Rechaza si está 'finalizada' o 'cancelada'.
    - Conserva todos los registros históricos en SQLite (no elimina registros).
    """
    if db_conn is None:
        raise CocinaServiceError("Conexión a base de datos no disponible.")

    comanda = repository.obtener_comanda_por_id(db_conn, comanda_id)
    if not comanda:
        raise CocinaComandaNoEncontradaError(f"No se encontró la comanda #{comanda_id}.")

    estado_actual = comanda['estado']

    if estado_actual == ESTADO_PENDIENTE:
        raise CocinaTransicionInvalidaError(
            f"No se puede finalizar la comanda #{comanda_id} porque todavía está pendiente. "
            "Debe iniciarse su preparación primero."
        )

    if estado_actual == ESTADO_CANCELADA:
        raise CocinaTransicionInvalidaError(
            f"No se puede finalizar la comanda #{comanda_id} porque fue cancelada."
        )

    if estado_actual == ESTADO_FINALIZADA:
        raise CocinaTransicionInvalidaError(
            f"La comanda #{comanda_id} ya fue finalizada previamente."
        )

    if estado_actual != ESTADO_EN_PREPARACION:
        raise CocinaTransicionInvalidaError(
            f"Transición inválida: no se puede finalizar una comanda en estado '{estado_actual}'."
        )

    try:
        actualizado = repository.actualizar_estado_comanda(
            db_conn,
            comanda_id=comanda_id,
            nuevo_estado=ESTADO_FINALIZADA,
            estado_esperado=ESTADO_EN_PREPARACION
        )

        if not actualizado:
            db_conn.rollback()
            raise CocinaConcurrenciaError(
                f"La comanda #{comanda_id} fue modificada simultáneamente. Por favor actualice el monitor."
            )

        db_conn.commit()
        logger.info("Comanda #%s marcada como 'finalizada' exitosamente.", comanda_id)
        return True

    except DatabaseError as err:
        db_conn.rollback()
        logger.error("Error al finalizar comanda #%s: %s", comanda_id, err)
        raise CocinaServiceError(f"No fue posible finalizar la comanda: {err}") from err
