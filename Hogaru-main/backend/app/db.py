"""Conexión a MySQL/MariaDB y helpers de consulta.

Cada request abre su propia conexión (dependencia `get_db`). Las escrituras NO se
confirman solas: el endpoint llama a `db.commit()` al final. Si algo falla antes,
la conexión se cierra y MySQL deshace todo (transacción atómica).
"""
import pymysql
from pymysql.cursors import DictCursor

from . import config


def nueva_conexion():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def get_db():
    """Dependencia de FastAPI: una conexión por request."""
    conn = nueva_conexion()
    try:
        yield conn
    finally:
        conn.close()  # sin commit previo => rollback automático


def uno(db, sql, params=()):
    """Devuelve la primera fila (dict) o None."""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def todos(db, sql, params=()):
    """Devuelve una lista de filas (dicts)."""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def insertar(db, sql, params=()):
    """Ejecuta un INSERT y devuelve el id autogenerado."""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


def actualizar(db, sql, params=()):
    """Ejecuta un UPDATE/DELETE y devuelve la cantidad de filas afectadas."""
    with db.cursor() as cur:
        return cur.execute(sql, params)
