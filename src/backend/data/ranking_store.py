"""Serving-store adapter: DuckDB (local/CI) or Neon Postgres (production).

SQL in query_engine / insights / draft_lab stays DuckDB-shaped (`?` placeholders,
unqualified table names). This module rewrites for Postgres and sets
`search_path` to `stats, app, public`.
"""
from __future__ import annotations

import logging
import math
import os
import re
import threading
from pathlib import Path
from typing import Any, Optional

from backend.core.config import config
from backend.core.exceptions import (
    DatabaseUnavailableError,
    PemSportsException,
    QueryEngineError,
    TableMissingError,
)
from backend.utils.team_normalization import normalize_team_abbr

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = Path(
    os.environ.get("NFL_STATS_DB_PATH", str(_PROJECT_ROOT / "data" / "nfl_stats.db"))
).resolve()

_thread_local = threading.local()
_logged_db_path = False
_local_generation = 0
_last_pg_generation: Optional[int] = None

_PRAGMA_RE = re.compile(
    r"^\s*PRAGMA\s+table_info\(\s*'([^']+)'\s*\)\s*$",
    re.IGNORECASE,
)
_SHOW_TABLES_RE = re.compile(r"^\s*SHOW\s+TABLES\s*$", re.IGNORECASE)


def qualify_relation(bare: str) -> str:
    """Return a FROM-clause identifier. Postgres relies on search_path."""
    return bare


def is_postgres() -> bool:
    return config.rankings_store == "postgres"


def bump_local_generation() -> int:
    global _local_generation
    _local_generation += 1
    return _local_generation


def local_generation() -> int:
    return _local_generation


def _duck_conn():
    import duckdb

    global _logged_db_path
    if not hasattr(_thread_local, "duck_conn"):
        if not _logged_db_path:
            logger.warning(
                "[DB PATH] NFL_STATS_DB_PATH=%r resolved_db_path=%s exists=%s",
                os.environ.get("NFL_STATS_DB_PATH"),
                _DB_PATH,
                _DB_PATH.exists(),
            )
            _logged_db_path = True
        if not _DB_PATH.exists():
            logger.error(
                "Serving database not found at %s. Run bake_db.py first.", _DB_PATH
            )
            raise DatabaseUnavailableError(
                f"Serving database not found at {_DB_PATH}. Run bake_db.py."
            )
        _thread_local.duck_conn = duckdb.connect(str(_DB_PATH), read_only=True)
    return _thread_local.duck_conn


def _pg_conn():
    import psycopg

    if not config.database_url:
        raise DatabaseUnavailableError(
            "RANKINGS_STORE=postgres requires DATABASE_URL."
        )
    if not hasattr(_thread_local, "pg_conn") or _thread_local.pg_conn.closed:
        conn = psycopg.connect(config.database_url, autocommit=True)
        conn.execute("SET search_path TO stats, app, public")
        _thread_local.pg_conn = conn
    return _thread_local.pg_conn


def get_store_conn() -> Any:
    """Thread-local serving connection (DuckDB or psycopg)."""
    if is_postgres():
        return _pg_conn()
    return _duck_conn()


def reset_store_conn() -> None:
    for attr in ("duck_conn", "pg_conn"):
        if hasattr(_thread_local, attr):
            try:
                getattr(_thread_local, attr).close()
            except Exception:
                pass
            delattr(_thread_local, attr)


def _rewrite_postgres_sql(sql: str) -> tuple[str, Optional[str]]:
    stripped = sql.strip()
    pragma = _PRAGMA_RE.match(stripped)
    if pragma:
        table = pragma.group(1).split(".")[-1]
        return (
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema = 'stats' AND table_name = %s",
            table,
        )
    if _SHOW_TABLES_RE.match(stripped):
        return (
            "SELECT table_name AS name FROM information_schema.tables "
            "WHERE table_schema = 'stats' ORDER BY table_name",
            None,
        )
    return sql.replace("?", "%s"), None


def _serialize_rows(description, rows) -> list[dict[str, Any]]:
    if description is None:
        return []
    columns = [desc[0].lower() for desc in description]
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        for k, v in row_dict.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                row_dict[k] = None
        for col in ("team", "opp", "opponent", "defense_team"):
            if col in row_dict and row_dict[col] is not None:
                row_dict[col] = normalize_team_abbr(row_dict[col])
        results.append(row_dict)
    return results


def execute_sql(
    sql: str,
    params: list[Any] | None = None,
    *,
    context: str,
) -> list[dict[str, Any]]:
    """Run serving SQL against the configured store."""
    params = list(params or [])

    def _run_duck() -> list[dict[str, Any]]:
        import duckdb

        conn = _duck_conn()
        cursor = conn.execute(sql, params)
        return _serialize_rows(cursor.description, cursor.fetchall())

    def _run_pg() -> list[dict[str, Any]]:
        pg_sql, extra = _rewrite_postgres_sql(sql)
        pg_params = [extra] if extra is not None else params
        conn = _pg_conn()
        cursor = conn.execute(pg_sql, pg_params)
        desc = cursor.description
        fetched = cursor.fetchall() if desc else []
        return _serialize_rows(desc, fetched)

    last_exc: Optional[BaseException] = None
    for attempt in range(2):
        try:
            if is_postgres():
                return _run_pg()
            return _run_duck()
        except PemSportsException:
            raise
        except Exception as exc:
            last_exc = exc
            name = type(exc).__name__
            if name == "IOException" and attempt == 0:
                logger.warning(
                    "Store IO error (%s), retrying with fresh connection: %s",
                    context,
                    exc,
                )
                reset_store_conn()
                continue
            break
    assert last_exc is not None
    _raise_store_error(last_exc, context)
    raise AssertionError("unreachable")


def _raise_store_error(exc: BaseException, context: str) -> None:
    name = type(exc).__name__
    msg = str(exc).lower()

    pg_undefined = False
    try:
        from psycopg.errors import UndefinedTable

        pg_undefined = isinstance(exc, UndefinedTable)
    except Exception:
        pg_undefined = "does not exist" in msg and "relation" in msg

    if name == "CatalogException" or pg_undefined:
        logger.warning("Table missing for %s: %s", context, exc)
        raise TableMissingError(f"Table for {context} is not baked.") from exc

    if name in {"BinderException", "ParserException", "UndefinedColumn"} or "syntax error" in msg:
        logger.exception("Query engine SQL error (%s)", context)
        raise QueryEngineError(f"SQL error querying {context}: {exc}") from exc

    logger.exception("Unexpected error in ranking store (%s)", context)
    raise QueryEngineError(f"Unexpected failure querying {context}: {exc}") from exc


def stats_generation() -> int:
    """Monotonic generation used in ranking cache keys."""
    global _last_pg_generation
    if not is_postgres():
        return local_generation()
    try:
        conn = _pg_conn()
        row = conn.execute(
            "SELECT generation FROM stats_generation WHERE id = 1"
        ).fetchone()
        gen = int(row[0]) if row else local_generation()
        _last_pg_generation = gen
        return gen
    except Exception:
        logger.warning(
            "Failed to read stats_generation from Postgres; using last known generation",
            exc_info=True,
        )
        if _last_pg_generation is not None:
            return _last_pg_generation
        return local_generation()


def bump_stats_generation(conn: Any) -> int:
    """Increment warehouse generation (ETL connection)."""
    conn.execute(
        "UPDATE app.stats_generation SET generation = generation + 1, "
        "updated_at = NOW() WHERE id = 1"
    )
    row = conn.execute(
        "SELECT generation FROM app.stats_generation WHERE id = 1"
    ).fetchone()
    return int(row[0]) if row else 0


def list_tables() -> set[str]:
    if is_postgres():
        rows = execute_sql("SHOW TABLES", context="schema.tables")
        return {str(r.get("name") or next(iter(r.values()))).lower() for r in rows}
    conn = _duck_conn()
    return {r[0].lower() for r in conn.execute("SHOW TABLES").fetchall()}


def health_payload() -> dict[str, Any]:
    """Used by /health. Never raises."""
    positions = ["QB", "RB", "WR", "TE", "K", "DST"]
    positions_available: list[str] = []
    data_files_found = 0
    status = "ok"
    try:
        tables = list_tables()
        for pos in positions:
            if f"{pos.lower()}_seasonal" in tables:
                positions_available.append(pos)
            for kind in ("weekly", "seasonal"):
                if f"{pos.lower()}_{kind}" in tables:
                    data_files_found += 1
        if not positions_available:
            status = "degraded"
    except Exception:
        status = "degraded"
    return {
        "status": status,
        "version": "1.0.0",
        "service": "pem-sports-api",
        "rankings_store": config.rankings_store,
        "data_files_found": data_files_found,
        "positions_available": positions_available,
    }
