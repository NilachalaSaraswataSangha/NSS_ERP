"""
NSS ERP — Database connection pools.

Two pools:
  - Read pool (nss_db_backend): SELECT-only, used by all read endpoints.
  - Write pool (nss_db_writer): INSERT/UPDATE/DELETE on auth + admin tables,
    used by Tier 5 authentication and administration endpoints.

No ORM — raw SQL queries against nss.* tables.
"""

import psycopg2
import psycopg2.pool

from api.config import settings

# ── Read pool (nss_db_backend — SELECT-only) ────────────────────────────

_read_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the shared read connection pool, creating it on first use."""
    global _read_pool
    if _read_pool is None or _read_pool.closed:
        settings.validate()
        _read_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=settings.DB_READ_POOL_MIN,
            maxconn=settings.DB_READ_POOL_MAX,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
    return _read_pool


# ── Write pool (nss_db_writer — Tier 5) ─────────────────────────────────

_write_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_write_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the shared write connection pool, creating it on first use."""
    global _write_pool
    if _write_pool is None or _write_pool.closed:
        settings.validate()
        settings.validate_auth()
        _write_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=settings.DB_WRITE_POOL_MIN,
            maxconn=settings.DB_WRITE_POOL_MAX,
            dbname=settings.DB_NAME,
            user=settings.DB_WRITE_USER,
            password=settings.DB_WRITE_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
    return _write_pool


# ── Pool lifecycle ───────────────────────────────────────────────────────

def close_pool() -> None:
    """Close all connections in both pools."""
    global _read_pool, _write_pool
    if _read_pool is not None and not _read_pool.closed:
        _read_pool.closeall()
        _read_pool = None
    if _write_pool is not None and not _write_pool.closed:
        _write_pool.closeall()
        _write_pool = None


# ── Connection generators (FastAPI dependencies) ────────────────────────

def get_connection():
    """
    Read connection (nss_db_backend — SELECT-only).

    Usage as a FastAPI dependency:
        def endpoint(conn=Depends(get_connection)): ...
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def get_write_connection():
    """
    Write connection (nss_db_writer — INSERT/UPDATE/DELETE).

    Auto-commits on success, rolls back on exception.
    Usage as a FastAPI dependency:
        def endpoint(conn=Depends(get_write_connection)): ...
    """
    pool = get_write_pool()
    conn = pool.getconn()
    try:
        conn.autocommit = False
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ── Health check ─────────────────────────────────────────────────────────

def check_connection() -> bool:
    """
    Test whether the database is reachable via the read pool.

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
