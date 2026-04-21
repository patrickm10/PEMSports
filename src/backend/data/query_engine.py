"""
DuckDB analytical query engine.

Design contract:
- Uses a persistent, indexed DuckDB serving layer (data/nfl_stats.db).
- This results in near-zero latency for analytical window queries.
- Bypasses PlainSkip optimizer bugs associated with virtual Parquet views.
- Optimized for cloud hosting (low memory, fast cold starts).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional
import threading
import duckdb

logger = logging.getLogger(__name__)

# Resolve paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "nfl_stats.db"

_thread_local = threading.local()

def _get_conn():
    """Returns a thread-local, read-only connection to the serving database."""
    if not hasattr(_thread_local, 'conn'):
        if not _DB_PATH.exists():
            logger.error(f"Serving database not found at {_DB_PATH}. Run bake_db.py first.")
            # Fallback to in-memory if DB missing (e.g. during fresh setup)
            _thread_local.conn = duckdb.connect()
        else:
            # Connect in READ_ONLY mode for production safety and performance
            _thread_local.conn = duckdb.connect(str(_DB_PATH), read_only=True)
    return _thread_local.conn

def _serialize_rows(cursor) -> list[dict[str, Any]]:
    """Convert cursor results to serialized dicts with NaN/Inf handling."""
    import math
    if cursor is None:
        return []
        
    columns = [desc[0].lower() for desc in cursor.description]
    results = []
    
    for row in cursor.fetchall():
        row_dict = dict(zip(columns, row))
        for k, v in row_dict.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    row_dict[k] = None
        results.append(row_dict)
    return results

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
    
    # Calculate rank dynamically based on filter
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

    try:
        cursor = _get_conn().execute(sql, params)
        return _serialize_rows(cursor)
    except Exception as e:
        logger.error(f"Query failed for {table}: {e}")
        return []

def query_seasons(position: str) -> list[int]:
    """Return available years for a position."""
    table = f"{position.lower()}_seasonal"
    try:
        rows = _get_conn().execute(
            f"SELECT DISTINCT CAST(year AS INTEGER) AS yr FROM {table} ORDER BY yr DESC"
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []

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

    try:
        cursor = _get_conn().execute(sql, params)
        return _serialize_rows(cursor)
    except Exception as e:
        logger.error(f"Weekly query failed for {table}: {e}")
        return []

def query_available_weeks(position: str, year: Optional[int] = None) -> list[int]:
    """Return distinct weeks available for a position."""
    table = f"{position.lower()}_weekly"
    try:
        if year is not None:
            rows = _get_conn().execute(
                f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {table} WHERE year = ? ORDER BY wk ASC",
                [float(year)],
            ).fetchall()
        else:
            rows = _get_conn().execute(
                f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {table} ORDER BY wk ASC"
            ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []

# ── Specialized Queries ───────────────────────────────────────────────────────

def query_player_impact_metrics(
    position: str,
    player_id: str,
    metric_type: str = "surface",
) -> list[dict[str, Any]]:
    """Analytical splits for performance metrics."""
    table = f"{position.lower()}_weekly"
    
    config = {
        "surface": {"col": "surface_type", "filter": "surface_type IS NOT NULL"},
        "venue": {"col": "indoor_outdoor", "filter": "indoor_outdoor IS NOT NULL"},
        "elevation": {
            "col": "CASE WHEN elevation >= 500 THEN 'High' WHEN elevation BETWEEN 100 AND 499 THEN 'Med' ELSE 'Low' END",
            "filter": "elevation IS NOT NULL"
        },
        "opponent": {"col": "opponent", "filter": "opponent IS NOT NULL"}
    }
    
    cfg = config.get(metric_type, config["surface"])
    col_expr = cfg["col"]
    filter_expr = cfg["filter"]
    
    sql = f"""
        SELECT 
            {col_expr} AS metric_label,
            ROUND(AVG(fpts), 2) AS avg_fpts,
            ROUND(AVG(fpts_ppr), 2) AS avg_fpts_ppr,
            COUNT(*) AS games_played
        FROM {table}
        WHERE player_id = ? AND {filter_expr}
        GROUP BY 1
        ORDER BY avg_fpts_ppr DESC
    """
    
    try:
        cursor = _get_conn().execute(sql, [player_id])
        return _serialize_rows(cursor)
    except Exception:
        return []

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
    try:
        cursor = _get_conn().execute(sql)
        return _serialize_rows(cursor)
    except Exception:
        return []

def query_player_profile(player_id: str, position: str) -> Optional[dict[str, Any]]:
    """Fetch all seasons for a player."""
    table = f"{position.lower()}_seasonal"
    try:
        cursor = _get_conn().execute(
            f"SELECT * FROM {table} WHERE player_id = ? ORDER BY year DESC",
            [player_id],
        )
        seasons = _serialize_rows(cursor)
        return {"seasons": seasons} if seasons else None
    except Exception:
        return None

def invalidate_view(position: str, weekly: bool = False) -> None:
    """NO-OP in persistent mode. Database is updated via bake_db.py."""
    pass
