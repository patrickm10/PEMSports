"""
PostgreSQL connection management and schema definitions.

Note: Rankings data remains in Parquet/DuckDB for performance.
Postgres is intended for transactional data:
- User accounts and preferences
- Saved comparisons/dashboards
- Data refresh logs (pipeline metadata)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

# Using psycopg for standard SQL operations
import psycopg
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Connection string: postgresql://[user[:password]@][host][:port]/[dbname]
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/nflstats")

_pool: Optional[AsyncConnectionPool] = None
_db_connected: bool = False

async def get_pool() -> AsyncConnectionPool:
    """Return the global connection pool, initializing it if necessary."""
    global _pool
    if _pool is None:
        logger.info("Initializing PostgreSQL connection pool...")
        # Use a short timeout so that local dev without DB falls back immediately
        _pool = AsyncConnectionPool(conninfo=DATABASE_URL, open=False, timeout=2.0)
        try:
            await _pool.open(timeout=2.0)
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


# ── Future Schema (Scaffolded) ────────────────────────────────────────────────

CREATE_SCHEMA_SQL = """
-- Tracking pipeline runs and data freshness
CREATE TABLE IF NOT EXISTS data_refresh_log (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    position VARCHAR(10) NOT NULL,
    rows_processed INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT
);

-- Future user accounts
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Future saved comparisons
CREATE TABLE IF NOT EXISTS saved_comparisons (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    comparison_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db():
    """Create initial schema if it doesn't exist."""
    global _db_connected
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(CREATE_SCHEMA_SQL)
            await conn.commit()
            logger.info("Successfully initialized PostgreSQL schema.")
            _db_connected = True
    except Exception as e:
        logger.warning("PostgreSQL initialization skipped/failed: %s", e)
        logger.info("Running without PostgreSQL support (common in development).")
        _db_connected = False


def is_db_connected() -> bool:
    """Check if the global connection pool is active for fallback branching."""
    return _db_connected
