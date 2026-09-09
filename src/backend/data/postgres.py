"""
PostgreSQL connection management.

OLTP lives in schema `app` (users, entitlements, refresh tokens).
Rankings warehouse lives in schema `stats` (published by ETL).

Environment policy:
- In `development`, a failed `init_db()` logs a warning and `_db_connected`
  stays False.
- In `staging` / `production`, any failure during `init_db()` re-raises.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import psycopg
from psycopg_pool import AsyncConnectionPool

from backend.core.config import config

logger = logging.getLogger(__name__)

DATABASE_URL = config.database_url

POOL_OPEN_TIMEOUT = 30.0

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "backend" / "migrations"
)

_pool: Optional[AsyncConnectionPool] = None
_db_connected: bool = False


class DatabaseUnavailable(RuntimeError):
    """Raised when Postgres is required but not reachable."""


async def _configure_connection(conn: psycopg.AsyncConnection) -> None:
    await conn.execute("SET search_path TO app, stats, public")


async def get_pool() -> AsyncConnectionPool:
    """Return the global connection pool, initializing it if necessary."""
    global _pool
    if _pool is None:
        logger.info("Initializing PostgreSQL connection pool...")
        _pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            open=False,
            timeout=POOL_OPEN_TIMEOUT,
            configure=_configure_connection,
        )
        try:
            await _pool.open(timeout=POOL_OPEN_TIMEOUT)
        except Exception as e:
            logger.warning("Failed to open connection pool: %s", e)
            _pool = None
            raise
    return _pool


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Provide a connection from the pool as an async context manager."""
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn


async def close_db():
    """Shutdown the connection pool."""
    global _pool, _db_connected
    if _pool:
        logger.info("Closing PostgreSQL connection pool...")
        await _pool.close()
        _pool = None
        _db_connected = False


def _migration_files() -> list[Path]:
    if not _MIGRATIONS_DIR.is_dir():
        return []
    return sorted(p for p in _MIGRATIONS_DIR.glob("*.sql") if p.is_file())


async def apply_migrations(conn: psycopg.AsyncConnection) -> None:
    files = _migration_files()
    async with conn.cursor() as cur:
        for path in files:
            sql = path.read_text(encoding="utf-8")
            try:
                await cur.execute(sql)
            except Exception as exc:
                if path.name.startswith("004"):
                    logger.warning("Optional migration %s skipped: %s", path.name, exc)
                    continue
                raise
    await conn.commit()
    logger.info("Applied %d Postgres migration files from %s", len(files), _MIGRATIONS_DIR)


async def init_db() -> None:
    """Open the pool and apply versioned SQL migrations.

    Raises:
        DatabaseUnavailable: In staging/production, if the pool cannot be
            opened or schema creation fails.
    """
    global _db_connected
    try:
        async with get_db_connection() as conn:
            await apply_migrations(conn)
            logger.info("Successfully initialized PostgreSQL schema.")
            _db_connected = True
    except Exception as e:
        _db_connected = False
        if config.is_development:
            logger.warning("PostgreSQL initialization skipped/failed: %s", e)
            logger.info("Running without PostgreSQL support (development only).")
            return
        logger.critical(
            "PostgreSQL is unreachable in %s mode — aborting startup: %s",
            config.app_env,
            e,
        )
        raise DatabaseUnavailable(
            f"Postgres required in {config.app_env} mode: {e}"
        ) from e


def is_db_connected() -> bool:
    """Check if the global connection pool is active for fallback branching."""
    return _db_connected
