"""
Capa de Acceso a Datos (Repository) para el módulo de Comandas.
Encapsula todas las consultas y operaciones SQL directas sobre las tablas
'comanda' y 'detalle_comanda', asegurando el uso de consultas parametrizadas.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Excepción para errores directos en la capa de persistencia."""
    pass

def insertar_comanda(db_conn, estado='pendiente'):
    """
    Inserta un nuevo registro de comanda.
    
    Parámetros:
        db_conn: Conexión activa a SQLite.
        estado (str): Estado inicial de la comanda ('pendiente').
        
    Retorna:
        int: Identificador de la comanda creada (comanda_id).
    """
    query = """
        INSERT INTO comanda (estado, fecha_hora_creacion, fecha_hora_actualizacion)
        VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (estado,))
        return cursor.lastrowid
    except sqlite3.Error as err:
        logger.error("Error al insertar comanda en SQLite: %s", err)
        raise DatabaseError(f"Error al insertar comanda: {err}") from err

def insertar_detalle(db_conn, comanda_id, producto_id, cantidad, especificaciones=''):
    """
    Inserta un registro en detalle_comanda.
    """
    query = """
        INSERT INTO detalle_comanda (comanda_id, producto_id, cantidad, especificaciones)
        VALUES (?, ?, ?, ?);
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (comanda_id, producto_id, cantidad, especificaciones))
        return cursor.lastrowid
    except sqlite3.Error as err:
        logger.error("Error al insertar detalle de comanda en SQLite: %s", err)
        raise DatabaseError(f"Error al insertar detalle de comanda: {err}") from err

def obtener_comandas(db_conn):
    """
    Obtiene la lista de comandas con resumen de productos y cantidades.
    Ordenadas descendentemente por fecha de creación (más recientes primero).
    """
    query = """
        SELECT 
            c.comanda_id,
            c.fecha_hora_creacion,
            c.fecha_hora_actualizacion,
            c.estado,
            COUNT(d.detalle_id) AS total_items,
            COALESCE(SUM(d.cantidad), 0) AS total_unidades
        FROM comanda c
        LEFT JOIN detalle_comanda d ON c.comanda_id = d.comanda_id
        GROUP BY c.comanda_id
        ORDER BY c.fecha_hora_creacion DESC, c.comanda_id DESC;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query)
        filas = cursor.fetchall()
        return [dict(f) for f in filas]
    except sqlite3.Error as err:
        logger.error("Error al consultar lista de comandas: %s", err)
        raise DatabaseError(f"Error al consultar comandas: {err}") from err

def obtener_comanda_por_id(db_conn, comanda_id):
    """
    Obtiene los datos principales de una comanda por su ID.
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
        logger.error("Error al consultar comanda por ID %s: %s", comanda_id, err)
        raise DatabaseError(f"Error al consultar comanda: {err}") from err

def obtener_detalles_por_comanda_id(db_conn, comanda_id):
    """
    Obtiene los detalles de una comanda con la información del producto asociado.
    """
    query = """
        SELECT 
            d.detalle_id,
            d.comanda_id,
            d.producto_id,
            d.cantidad,
            COALESCE(d.especificaciones, '') AS especificaciones,
            p.nombre AS producto_nombre,
            p.descripcion AS producto_descripcion,
            p.activo AS producto_activo
        FROM detalle_comanda d
        JOIN producto p ON d.producto_id = p.producto_id
        WHERE d.comanda_id = ?
        ORDER BY d.detalle_id ASC;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (comanda_id,))
        filas = cursor.fetchall()
        return [dict(f) for f in filas]
    except sqlite3.Error as err:
        logger.error("Error al consultar detalles de comanda %s: %s", comanda_id, err)
        raise DatabaseError(f"Error al consultar detalles de comanda: {err}") from err

def eliminar_detalles_por_comanda_id(db_conn, comanda_id):
    """
    Elimina todos los detalles de una comanda (utilizado durante la modificación).
    """
    query = "DELETE FROM detalle_comanda WHERE comanda_id = ?;"
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (comanda_id,))
    except sqlite3.Error as err:
        logger.error("Error al eliminar detalles de comanda %s: %s", comanda_id, err)
        raise DatabaseError(f"Error al eliminar detalles de comanda: {err}") from err

def actualizar_fecha_modificacion(db_conn, comanda_id):
    """
    Actualiza el campo fecha_hora_actualizacion con el timestamp actual.
    """
    query = """
        UPDATE comanda
        SET fecha_hora_actualizacion = CURRENT_TIMESTAMP
        WHERE comanda_id = ?;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (comanda_id,))
    except sqlite3.Error as err:
        logger.error("Error al actualizar fecha de comanda %s: %s", comanda_id, err)
        raise DatabaseError(f"Error al actualizar fecha de comanda: {err}") from err

def actualizar_estado_comanda(db_conn, comanda_id, nuevo_estado):
    """
    Actualiza el estado de la comanda y su fecha de modificación.
    """
    query = """
        UPDATE comanda
        SET estado = ?, fecha_hora_actualizacion = CURRENT_TIMESTAMP
        WHERE comanda_id = ?;
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (nuevo_estado, comanda_id))
    except sqlite3.Error as err:
        logger.error("Error al actualizar estado de comanda %s a '%s': %s", comanda_id, nuevo_estado, err)
        raise DatabaseError(f"Error al actualizar estado de comanda: {err}") from err

def obtener_producto_por_id(db_conn, producto_id):
    """
    Consulta un producto por su ID para verificar existencia y si está activo.
    """
    query = "SELECT producto_id, nombre, descripcion, activo FROM producto WHERE producto_id = ?;"
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, (producto_id,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    except sqlite3.Error as err:
        logger.error("Error al verificar producto %s: %s", producto_id, err)
        raise DatabaseError(f"Error al verificar producto: {err}") from err
