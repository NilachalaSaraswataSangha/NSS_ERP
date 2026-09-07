"""
NSS ERP — Database connection pool.

Uses psycopg2 with a simple connection-pool pattern.
The FastAPI application connects as nss_db_backend (read-only in Tier 0).

No ORM — raw SQL queries against nss.* tables.
"""

import psycopg2
import psycopg2.pool

from api.config import settings

# Module-level pool — initialised on first call to get_pool()
_pool: psycopg2.pool.SimpleConnectionPool | None = None


def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Return the shared connection pool, creating it on first use."""
    global _pool
    if _pool is None or _pool.closed:
        settings.validate()
        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
    return _pool


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None


def get_connection():
    """
    Context-manager-compatible connection getter.

    Usage as a FastAPI dependency:
        conn = get_pool().getconn()
        try:
            yield conn
        finally:
            get_pool().putconn(conn)
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def check_connection() -> bool:
    """
    Test whether the database is reachable.

    Returns True if a simple query succeeds, False otherwise.
    Does not leak connection details on failure.
    """
    try:
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            pool.putconn(conn)
    except Exception:
        return False
