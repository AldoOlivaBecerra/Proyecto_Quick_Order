"""
Capa de Acceso a Datos (Repository) para el módulo de Cocina.
Encapsula las consultas optimizadas para el monitor de cocina (KDS):
- Consulta de comandas activas ('pendiente' y 'en preparación') ordenadas por FIFO.
- Transiciones atómicas de estado con comprobación de estado previo (concurrencia).
- Actualización de timestamp de última modificación.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Excepción para errores de base de datos en la capa de persistencia de Cocina."""
    pass

def obtener_comandas_activas(db_conn):
    """
    Obtiene todas las comandas en estado 'pendiente' y 'en preparación',
    ordenadas cronológicamente de forma ascendente (FIFO: primero en entrar, primero en salir).
    Incluye todos los detalles de productos y especificaciones asociados.
    
    Retorna:
        list[dict]: Lista de comandas estructuradas con sus ítems.
    """
    # 1. Consultar encabezados de comandas activas
    query_comandas = """
        SELECT 
            comanda_id,
            fecha_hora_creacion,
            fecha_hora_actualizacion,
            estado
        FROM comanda
        WHERE estado IN ('pendiente', 'en preparación')
        ORDER BY fecha_hora_creacion ASC, comanda_id ASC;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query_comandas)
        filas_comandas = cursor.fetchall()

        if not filas_comandas:
            return []

        comandas_dict = {}
        for row in filas_comandas:
            cid = row['comanda_id']
            comandas_dict[cid] = {
                'comanda_id': cid,
                'fecha_hora_creacion': row['fecha_hora_creacion'],
                'fecha_hora_actualizacion': row['fecha_hora_actualizacion'],
                'estado': row['estado'],
                'items': []
            }

        # 2. Consultar detalles de las comandas activas
        placeholders = ','.join('?' for _ in comandas_dict.keys())
        query_detalles = f"""
            SELECT 
                d.detalle_id,
                d.comanda_id,
                d.producto_id,
                d.cantidad,
                COALESCE(d.especificaciones, '') AS especificaciones,
                p.nombre AS producto_nombre
            FROM detalle_comanda d
            JOIN producto p ON d.producto_id = p.producto_id
            WHERE d.comanda_id IN ({placeholders})
            ORDER BY d.detalle_id ASC;
        """
        cursor.execute(query_detalles, list(comandas_dict.keys()))
        filas_detalles = cursor.fetchall()

        for det in filas_detalles:
            cid = det['comanda_id']
            if cid in comandas_dict:
                comandas_dict[cid]['items'].append({
                    'detalle_id': det['detalle_id'],
                    'producto_id': det['producto_id'],
                    'producto_nombre': det['producto_nombre'],
                    'cantidad': det['cantidad'],
                    'especificaciones': det['especificaciones']
                })

        return list(comandas_dict.values())

    except sqlite3.Error as err:
        logger.error("Error al consultar comandas activas para Cocina: %s", err)
        raise DatabaseError(f"Error al consultar comandas de cocina: {err}") from err

def obtener_comanda_por_id(db_conn, comanda_id):
    """
    Obtiene el estado actual y metadatos de una comanda específica.
    """
    query = """
        SELECT comanda_id, fecha_hora_creacion, fecha_hora_actualizacion, estado
        FROM comanda
        WHERE comanda_id = ?;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (comanda_id,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    except sqlite3.Error as err:
        logger.error("Error al consultar comanda #%s en Cocina: %s", comanda_id, err)
        raise DatabaseError(f"Error al consultar comanda: {err}") from err

def actualizar_estado_comanda(db_conn, comanda_id, nuevo_estado, estado_esperado):
    """
    Actualiza el estado de una comanda de forma atómica y protegida.
    Solo aplica el cambio si el estado actual en la base de datos coincide
    con 'estado_esperado', evitando condiciones de carrera entre caja y cocina.
    
    Retorna:
        bool: True si se actualizó exactamente 1 registro, False si el estado previo no coincidió.
    """
    query = """
        UPDATE comanda
        SET estado = ?, fecha_hora_actualizacion = CURRENT_TIMESTAMP
        WHERE comanda_id = ? AND estado = ?;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (nuevo_estado, comanda_id, estado_esperado))
        return cursor.rowcount > 0
    except sqlite3.Error as err:
        logger.error(
            "Error al actualizar comanda #%s de '%s' a '%s': %s",
            comanda_id, estado_esperado, nuevo_estado, err
        )
        raise DatabaseError(f"Error al actualizar estado en cocina: {err}") from err
