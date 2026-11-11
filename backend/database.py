"""
Capa de acceso a datos de la API.

Responsabilidades:
  * Leer la cadena de conexión desde la variable de entorno DATABASE_URL.
  * Mantener un pool de conexiones a PostgreSQL (Neon).
  * Traducir los errores de psycopg2 a la excepción controlada ErrorBaseDatos,
    que la aplicación convierte en una respuesta HTTP 503 con un mensaje claro.

El pool es perezoso (se crea con la primera consulta) para que la aplicación
pueda arrancar aunque DATABASE_URL todavía no esté configurada; así GET /health
explica el problema en lugar de que el proceso muera al iniciar.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

MIN_CONEXIONES = 1
MAX_CONEXIONES = 8
ESPERA_MAXIMA_SEGUNDOS = 10

MENSAJE_SIN_CONFIGURAR = (
    "La variable de entorno DATABASE_URL no está configurada. Copia "
    ".env.example a .env y coloca la cadena de conexión de Neon "
    "(Dashboard de Neon -> Connect -> Connection string)."
)


class ErrorBaseDatos(Exception):
    """Error controlado de la capa de datos (la API responde HTTP 503)."""


_pool_privado: "pg_pool.SimpleConnectionPool | None" = None


# ---------------------------------------------------------------------------
# Configuración del pool
# ---------------------------------------------------------------------------
def url_conexion() -> str | None:
    """
    Devuelve DATABASE_URL lista para usarse con psycopg2.

    Corrige dos detalles habituales de las cadenas de conexión copiadas de Neon:
      * 'postgres://' (formato viejo) -> 'postgresql://'
      * agrega 'sslmode=require' si no viene incluido (Neon exige TLS).
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return None
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def _crear_pool() -> pg_pool.SimpleConnectionPool:
    url = url_conexion()
    if not url:
        raise ErrorBaseDatos(MENSAJE_SIN_CONFIGURAR)
    try:
        return pg_pool.SimpleConnectionPool(
            MIN_CONEXIONES,
            MAX_CONEXIONES,
            dsn=url,
            connect_timeout=15,
            application_name="api_solicitudes_soporte",
        )
    except psycopg2.Error as exc:
        raise ErrorBaseDatos(
            "No fue posible conectar con PostgreSQL (Neon). Revisa que la cadena "
            "DATABASE_URL sea correcta, que incluya sslmode=require y que el "
            "proyecto de Neon no esté suspendido."
        ) from exc


def _obtener_pool() -> pg_pool.SimpleConnectionPool:
    global _pool_privado
    if _pool_privado is None:
        _pool_privado = _crear_pool()
    return _pool_privado


def _cerrar_pool() -> None:
    """Cierra y descarta el pool para forzar su recreación (Neon reinicia conexiones)."""
    global _pool_privado
    if _pool_privado is not None:
        try:
            _pool_privado.closeall()
        except Exception:  # noqa: BLE001 - el pool pudo quedar en mal estado
            pass
        _pool_privado = None


def mensaje_legible(exc: BaseException) -> str:
    """Traduce los errores más comunes de PostgreSQL a un mensaje entendible."""
    if isinstance(exc, (psycopg2.OperationalError, psycopg2.InterfaceError)):
        return (
            "Se perdió la conexión con la base de datos (Neon). Verifica "
            "DATABASE_URL y que el proyecto no esté suspendido por inactividad."
        )
    if isinstance(exc, psycopg2.errors.UndefinedTable):
        return (
            "No existe la tabla 'solicitudes'. Ejecuta database/schema.sql en el "
            "SQL Editor de Neon."
        )
    if isinstance(exc, psycopg2.errors.UndefinedColumn):
        return (
            "La tabla 'solicitudes' no tiene la estructura esperada. Vuelve a "
            "ejecutar database/schema.sql."
        )
    if isinstance(exc, psycopg2.errors.UniqueViolation):
        return "Ya existe un registro con ese valor único (folio o id_externo)."
    if isinstance(exc, psycopg2.errors.CheckViolation):
        return "Un dato no cumple las restricciones definidas en la tabla solicitudes."
    return "Ocurrió un error al consultar la base de datos."


# ---------------------------------------------------------------------------
# Contexto de conexión
# ---------------------------------------------------------------------------
@contextmanager
def conexion() -> Iterator[psycopg2.extensions.connection]:
    """
    Entrega una conexión del pool y hace commit/rollback automáticamente.

    Ejemplo:
        with conexion() as con:
            with con.cursor() as cur:
                cur.execute(...)
    """
    pool_actual = _obtener_pool()
    try:
        con = pool_actual.getconn()
    except psycopg2.Error as exc:
        _cerrar_pool()
        raise ErrorBaseDatos(mensaje_legible(exc)) from exc

    try:
        yield con
        con.commit()
    except psycopg2.Error as exc:
        try:
            con.rollback()
        except psycopg2.Error:
            pass
        # Si el problema fue de red/conexión, el pool queda inservible:
        if isinstance(exc, (psycopg2.OperationalError, psycopg2.InterfaceError)):
            _cerrar_pool()
        raise ErrorBaseDatos(mensaje_legible(exc)) from exc
    except Exception:
        try:
            con.rollback()
        except psycopg2.Error:
            pass
        raise
    finally:
        try:
            pool_actual.putconn(con)
        except Exception:  # noqa: BLE001 - el pool pudo haberse cerrado antes
            _cerrar_pool()


# ---------------------------------------------------------------------------
# Operaciones públicas
# ---------------------------------------------------------------------------
def consultar_varios(sql: str, parametros: tuple = ()) -> list[dict]:
    """Ejecuta un SELECT (o INSERT/UPDATE ... RETURNING) y regresa las filas como diccionarios."""
    with conexion() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, parametros)
            if cursor.description is None:
                return []
            return [dict(fila) for fila in cursor.fetchall()]


def consultar_uno(sql: str, parametros: tuple = ()) -> dict | None:
    """Igual que consultar_varios pero regresa solo la primera fila (o None)."""
    filas = consultar_varios(sql, parametros)
    return filas[0] if filas else None


def ejecutar(sql: str, parametros: tuple = ()) -> int:
    """Ejecuta un INSERT/UPDATE/DELETE y regresa el número de filas afectadas."""
    with conexion() as con:
        with con.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.rowcount


def hay_conexion() -> bool:
    """Indica si la base de datos responde (se usa en GET /health)."""
    try:
        fila = consultar_uno("SELECT 1 AS ok;")
        return bool(fila and fila.get("ok") == 1)
    except ErrorBaseDatos:
        return False
