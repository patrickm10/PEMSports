"""
DuckDB analytical query engine.

Design contract:
- Uses a persistent, indexed DuckDB serving layer (data/nfl_stats.db).
- This results in near-zero latency for analytical window queries.
- Bypasses PlainSkip optimizer bugs associated with virtual Parquet views.
- Optimized for cloud hosting (low memory, fast cold starts).

Error-handling contract:
- `[]` is reserved for the case where the SQL query ran successfully and
  returned zero rows for the requested filters. It is NOT a generic error
  sentinel.
- Missing tables raise `TableMissingError` (→ 404).
- Missing DB file raises `DatabaseUnavailableError` (→ 503).
- Any other DuckDB failure raises `QueryEngineError` (→ 500).
The global handler in `main.py` maps these to HTTP responses.
"""
from __future__ import annotations

import logging
import math
import os
import threading
from pathlib import Path
from typing import Any, Optional

import duckdb

from backend.core.exceptions import (
    DatabaseUnavailableError,
    NFLStatsException,
    QueryEngineError,
    TableMissingError,
)

logger = logging.getLogger(__name__)

# Resolve paths — __file__ is under src/backend/data/, so four parents = repo root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = Path(
    os.environ.get("NFL_STATS_DB_PATH", str(_PROJECT_ROOT / "data" / "nfl_stats.db"))
).resolve()

_thread_local = threading.local()


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Return a thread-local, read-only connection to the serving database.

    Raises:
        DatabaseUnavailableError: If the baked DB file does not exist.
            We intentionally do NOT fall back to an empty in-memory
            connection, which used to make missing-database errors look
            identical to empty-result responses.
    """
    if not hasattr(_thread_local, "conn"):
        if not _DB_PATH.exists():
            logger.error(
                "Serving database not found at %s. Run bake_db.py first.", _DB_PATH
            )
            raise DatabaseUnavailableError(
                f"Serving database not found at {_DB_PATH}. Run bake_db.py."
            )
        _thread_local.conn = duckdb.connect(str(_DB_PATH), read_only=True)
    return _thread_local.conn


def _serialize_rows(cursor) -> list[dict[str, Any]]:
    """Convert cursor results to serialized dicts with NaN/Inf handling."""
    if cursor is None:
        return []

    columns = [desc[0].lower() for desc in cursor.description]
    results: list[dict[str, Any]] = []

    for row in cursor.fetchall():
        row_dict = dict(zip(columns, row))
        for k, v in row_dict.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                row_dict[k] = None
        results.append(row_dict)
    return results


def _execute(sql: str, params: list[Any] | None = None, *, context: str) -> list[dict[str, Any]]:
    """Run `sql` with the shared connection, translating duckdb errors.

    `context` is a short label used in log messages (e.g. "qb_weekly").
    """
    try:
        cursor = _get_conn().execute(sql, params or [])
        return _serialize_rows(cursor)
    except duckdb.CatalogException as exc:
        logger.warning("Table missing for %s: %s", context, exc)
        raise TableMissingError(f"Table for {context} is not baked.") from exc
    except (duckdb.BinderException, duckdb.ParserException) as exc:
        logger.exception("Query engine SQL error (%s)", context)
        raise QueryEngineError(f"SQL error querying {context}: {exc}") from exc
    except duckdb.IOException as exc:
        logger.exception("DuckDB IO error (%s)", context)
        raise DatabaseUnavailableError(
            f"DuckDB IO failure while querying {context}: {exc}"
        ) from exc
    except NFLStatsException:
        raise
    except Exception as exc:  # noqa: BLE001 - final safety net, re-raised as typed
        logger.exception("Unexpected error in query engine (%s)", context)
        raise QueryEngineError(f"Unexpected failure querying {context}: {exc}") from exc


# ── Seasonal Rankings ─────────────────────────────────────────────────────────

def query_rankings(
    position: str,
    year: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query pre-baked seasonal rankings."""
    table = f"{position.lower()}_seasonal"

    conditions: list[str] = []
    params: list[Any] = []

    if year is not None:
        conditions.append("year = ?")
        params.append(float(year))

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY year
            ORDER BY fpts_ppr DESC NULLS LAST, fpts DESC NULLS LAST
        ) AS rank
    FROM {table}{where_clause}
    ORDER BY year DESC, rank ASC
    """

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    return _execute(sql, params, context=table)


def query_seasons(position: str) -> list[int]:
    """Return available years for a position."""
    table = f"{position.lower()}_seasonal"
    rows = _execute(
        f"SELECT DISTINCT CAST(year AS INTEGER) AS yr FROM {table} ORDER BY yr DESC",
        context=f"{table} (seasons)",
    )
    return [int(r["yr"]) for r in rows if r.get("yr") is not None]


# ── Weekly Rankings ───────────────────────────────────────────────────────────

def query_weekly_rankings(
    position: str,
    year: Optional[int] = None,
    week: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query pre-baked and indexed weekly rankings."""
    table = f"{position.lower()}_weekly"

    conditions: list[str] = []
    params: list[Any] = []

    if year is not None:
        conditions.append("year = ?")
        params.append(float(year))
    if week is not None:
        conditions.append("week = ?")
        params.append(float(week))

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY year, week
            ORDER BY fpts_ppr DESC NULLS LAST, fpts DESC NULLS LAST
        ) AS rank
    FROM {table}{where_clause}
    ORDER BY year DESC, week DESC, rank ASC
    """

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    return _execute(sql, params, context=table)


def query_available_weeks(position: str, year: Optional[int] = None) -> list[int]:
    """Return distinct weeks available for a position."""
    table = f"{position.lower()}_weekly"
    if year is not None:
        rows = _execute(
            f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {table} WHERE year = ? ORDER BY wk ASC",
            [float(year)],
            context=f"{table} (weeks)",
        )
    else:
        rows = _execute(
            f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {table} ORDER BY wk ASC",
            context=f"{table} (weeks)",
        )
    return [int(r["wk"]) for r in rows if r.get("wk") is not None]


# ── Specialized Queries ───────────────────────────────────────────────────────

def query_player_impact_metrics(
    position: str,
    player_id: str,
    metric_type: str = "surface",
) -> list[dict[str, Any]]:
    """Analytical splits for performance metrics."""
    table = f"{position.lower()}_weekly"

    metric_cfg = {
        "surface": {"col": "surface_type", "filter": "surface_type IS NOT NULL"},
        "venue": {"col": "indoor_outdoor", "filter": "indoor_outdoor IS NOT NULL"},
        "elevation": {
            "col": (
                "CASE WHEN elevation >= 500 THEN 'High' "
                "WHEN elevation BETWEEN 100 AND 499 THEN 'Med' "
                "ELSE 'Low' END"
            ),
            "filter": "elevation IS NOT NULL",
        },
        "opponent": {"col": "opponent", "filter": "opponent IS NOT NULL"},
    }

    cfg = metric_cfg.get(metric_type, metric_cfg["surface"])

    sql = f"""
        SELECT
            {cfg['col']} AS metric_label,
            ROUND(AVG(fpts), 2) AS avg_fpts,
            ROUND(AVG(fpts_ppr), 2) AS avg_fpts_ppr,
            COUNT(*) AS games_played
        FROM {table}
        WHERE player_id = ? AND {cfg['filter']}
        GROUP BY 1
        ORDER BY avg_fpts_ppr DESC
    """

    return _execute(sql, [player_id], context=f"{table} (impact/{metric_type})")


def query_team_defense_stats(position: str) -> list[dict[str, Any]]:
    """Average points allowed by defense to a position."""
    table = f"{position.lower()}_weekly"
    sql = f"""
        SELECT
            opponent AS defense_team,
            ROUND(AVG(fpts_ppr), 2) AS avg_points_allowed,
            COUNT(*) AS game_count
        FROM {table}
        WHERE opponent IS NOT NULL
        GROUP BY opponent
        ORDER BY avg_points_allowed DESC
    """
    return _execute(sql, context=f"{table} (defense)")


def query_player_profile(player_id: str, position: str) -> Optional[dict[str, Any]]:
    """Fetch all seasons for a player."""
    table = f"{position.lower()}_seasonal"
    seasons = _execute(
        f"SELECT * FROM {table} WHERE player_id = ? ORDER BY year DESC",
        [player_id],
        context=f"{table} (profile)",
    )
    return {"seasons": seasons} if seasons else None


def invalidate_view(position: str, weekly: bool = False) -> None:
    """NO-OP in persistent mode. Database is updated via bake_db.py."""
    pass
