"""
DuckDB analytical query engine.

Design contract:
- This module is the ONLY place that knows about file paths and storage formats.
- The service layer calls query functions; it never touches files directly.
- DuckDB reads CSV/Parquet via read_csv_auto / read_parquet — no intermediate
  Polars DataFrames in the hot path. Polars is used for transformation work
  in the pipeline layer.

Initialization:
- A module-level in-memory DuckDB connection is created once per process.
- Views are registered lazily per position on first access.
- All queries use parameterized statements (? placeholders) to prevent
  any injection risk from user-supplied values.

Storage fallback:
- Prefers Parquet (columnar, compressed, faster reads).
- Falls back to CSV if Parquet not present.
- This logic lives exclusively here — nothing else decides what file to read.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import duckdb

logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (not CWD).
# query_engine.py lives at src/backend/data/query_engine.py
# → .parent = data/ → .parent = backend/ → .parent = src/ → .parent = project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data" / "rankings"
_METADATA_DIR = _PROJECT_ROOT / "data" / "nfl_metadata"
_LOCAL_DATA_DIR = _PROJECT_ROOT / "data_local" / "raw_scrapes"

import threading

_thread_local = threading.local()

def _get_conn():
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = duckdb.connect()
    return _thread_local.conn

def _get_registered_views():
    if not hasattr(_thread_local, 'views'):
        _thread_local.views = set()
    return _thread_local.views




# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_data_path(position_upper: str, suffix: str = "historical") -> Path:
    """
    Return the best available data file for a position.
    1. Tracked Parquet (data/rankings/{POS}_{SUFFIX}.parquet)
    2. Local CSV fallback (data_local/raw_scrapes/{POS}_*.csv)
    """
    # Standardize 'historical' to 'seasonal' for our new naming convention
    type_suffix = "weekly" if suffix == "weekly" else "seasonal"
    
    parquet = _DATA_DIR / f"{position_upper.upper()}_{type_suffix}.parquet"
    if parquet.exists():
        return parquet

    # Fallback to Local CSV
    csv_pattern = f"{position_upper.upper()}_*_{type_suffix}.csv"
    local_csvs = list(_LOCAL_DATA_DIR.glob(csv_pattern))
    if local_csvs:
        return local_csvs[0]

    raise FileNotFoundError(
        f"No {type_suffix} data found for {position_upper}. "
        f"Checked: {parquet}"
    )


def _make_source_expr(data_path: Path) -> str:
    """Build a DuckDB source expression for a data file."""
    path_str = str(data_path).replace("\\", "/")
    
    if data_path.suffix == ".parquet":
        return f"read_parquet('{path_str}')"
        
    # Fallback to CSV
    return f"read_csv_auto('{path_str}', header=true, ignore_errors=true)"




def _serialize_rows(df) -> list[dict[str, Any]]:
    """
    Convert a Pandas DataFrame into a list of plain Python dicts.
    Optimized for performance and JSON safety (NaN/Inf -> None).
    """
    import numpy as np
    
    # Pre-calculate column names to avoid repeated attribute access
    columns = [c.lower() for c in df.columns]
    
    # to_dict('records') is generally fast, but we need to clean types
    results = df.to_dict(orient="records")
    
    for row in results:
        # We modify in-place or create new dicts. 
        # For simplicity and speed in Python, we'll iterate the items.
        for k, v in list(row.items()):
            # DuckDB/Pandas often return float64 for missing ints
            if isinstance(v, (float, np.floating)):
                if np.isnan(v) or np.isinf(v):
                    row[k] = None
                else:
                    row[k] = float(v)
            elif hasattr(v, "item"):  # handles numpy scalars
                row[k] = v.item()
            
            # Ensure keys are lowercase for frontend consistency
            lowered_k = k.lower()
            if lowered_k != k:
                row[lowered_k] = row.pop(k)
                
    return results


# ── Seasonal Views ────────────────────────────────────────────────────────────

def _ensure_view(position_upper: str) -> str:
    """
    Register a DuckDB view for seasonal data if not already registered.
    The view adds a pre-computed `rank` window column partitioned by year.

    Dynamically inspects source columns to avoid adding duplicate NULL
    placeholders for enrichment columns that already exist in the data.
    """
    view_name = f"v_{position_upper.lower()}"
    if view_name in _get_registered_views():
        return view_name

    try:
        data_path = _resolve_data_path(position_upper, "historical")
    except FileNotFoundError:
        return ""

    source = _make_source_expr(data_path)

    try:
        source_cols_df = _get_conn().execute(f"SELECT * FROM {source} LIMIT 0").fetchdf()
        physical_cols = list(source_cols_df.columns)
    except Exception as e:
        logger.warning("Could not introspect source columns for %s: %s", source, e)
        physical_cols = []

    # Case-insensitive check for 'rank' to avoid duplicate column errors
    exclude_cols = [f'"{c}"' for c in physical_cols if c.lower() == 'rank']
    exclude_clause = f" EXCLUDE ({', '.join(exclude_cols)})" if exclude_cols else ""

    try:
        _get_conn().execute(f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT
                s.*{exclude_clause},
                ROW_NUMBER() OVER (
                    PARTITION BY s.year
                    ORDER BY
                        TRY_CAST(s.fpts_ppr AS DOUBLE) DESC NULLS LAST,
                        TRY_CAST(s.fpts AS DOUBLE) DESC NULLS LAST
                ) AS rank
            FROM {source} s
        """)
        _get_registered_views().add(view_name)
        logger.info("Registered DuckDB view: %s → %s", view_name, data_path.name)
    except Exception as e:
        logger.error("Failed to register view %s: %s", view_name, e)
        raise
    return view_name


def query_rankings(
    position: str,
    year: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Query season rankings for a position from DuckDB.
    Filters by year when provided.
    """
    view = _ensure_view(position.upper())
    if not view:
        return []

    if year is not None:
        sql = f"SELECT * FROM {view} WHERE CAST(year AS INTEGER) = ?"
        df = _get_conn().execute(sql, [year]).fetchdf()
    else:
        sql = f"SELECT * FROM {view}"
        df = _get_conn().execute(sql).fetchdf()
        
    # Bypass DuckDB PlainSkip string bugs
    df = df.sort_values(["year", "rank"], ascending=[False, True])

    # Bypass DuckDB PlainSkip bug by paginating in memory
    if limit is not None:
        df = df.iloc[offset:offset+limit]
    elif offset > 0:
        df = df.iloc[offset:]

    return _serialize_rows(df)


def query_seasons(position: str) -> list[int]:
    """Return available years for a position."""
    view = _ensure_view(position.upper())
    if not view:
        return []

    rows = _get_conn().execute(
        f"SELECT DISTINCT CAST(year AS INTEGER) AS yr FROM {view} ORDER BY yr DESC"
    ).fetchall()
    return [r[0] for r in rows]


# ── Weekly Views ──────────────────────────────────────────────────────────────

def _ensure_weekly_view(position_upper: str) -> str:
    """
    Register a DuckDB view for weekly data if not already registered.
    Ranks players within each year+week partition by fpts_ppr.

    Dynamically inspects source columns to avoid EXCLUDE errors when
    enrichment columns are absent from the source data.
    """
    view_name = f"v_{position_upper.lower()}_weekly"
    if view_name in _get_registered_views():
        return view_name

    try:
        data_path = _resolve_data_path(position_upper, "weekly")
    except FileNotFoundError:
        # Gracefully handle missing position files (e.g. DST weekly if not yet generated)
        return ""

    source = _make_source_expr(data_path)

    # Enrichment columns that the matchup join provides.
    MATCHUP_COLS = {
        "opponent", "stadium_name", "city", "state",
        "indoor_outdoor", "surface_type", "elevation", "game_result",
        "temp", "humidity", "wind"
    }

    # Introspect the source file's column names
    try:
        source_cols_df = _get_conn().execute(
            f"SELECT * FROM {source} LIMIT 0"
        ).fetchdf()
        physical_cols = list(source_cols_df.columns)
        source_cols = {c.lower() for c in physical_cols}
    except Exception:
        physical_cols = []
        source_cols = set()
        
    exclude_cols = [f'"{c}"' for c in physical_cols if c.lower() == 'rank']
    exclude_clause = f" EXCLUDE ({', '.join(exclude_cols)})" if exclude_cols else ""

    # Dynamically add NULL placeholders only for columns NOT already in source.
    null_placeholders = []
    for col_name in sorted(MATCHUP_COLS):
        if col_name not in source_cols:
            col_type = "DOUBLE" if col_name in {"elevation", "temp", "humidity", "wind"} else "VARCHAR"
            null_placeholders.append(
                f"CAST(NULL AS {col_type}) AS {col_name}"
            )

    extra_cols = (",\n            " + ",\n            ".join(null_placeholders) + ",") if null_placeholders else ","

    _get_conn().execute(f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT
            s.*{exclude_clause}{extra_cols}
            ROW_NUMBER() OVER (
                PARTITION BY s.year, s.week
                ORDER BY
                    TRY_CAST(s.fpts_ppr AS DOUBLE) DESC NULLS LAST,
                    TRY_CAST(s.fpts AS DOUBLE) DESC NULLS LAST
            ) AS rank
        FROM {source} s
    """)

    _get_registered_views().add(view_name)
    logger.info("Registered DuckDB weekly view: %s → %s", view_name, data_path.name)
    return view_name


def query_weekly_rankings(
    position: str,
    year: Optional[int] = None,
    week: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Query weekly rankings for a position from DuckDB.
    Filters by year and/or week when provided.
    Filters are pushed into SQL to avoid full table scans.
    """
    view = _ensure_weekly_view(position.upper())
    if not view:
        return []

    conditions: list[str] = []
    params: list[Any] = []

    if year is not None:
        conditions.append("CAST(year AS INTEGER) = ?")
        params.append(year)
    if week is not None:
        conditions.append("CAST(week AS INTEGER) = ?")
        params.append(week)

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM {view}{where_clause} ORDER BY year DESC, week DESC, rank ASC"

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    elif offset > 0:
        sql += f" OFFSET {int(offset)}"

    df = _get_conn().execute(sql, params).fetchdf()
    return _serialize_rows(df)


def query_available_weeks(position: str, year: Optional[int] = None) -> list[int]:
    """Return distinct weeks available for a position, optionally filtered by year."""
    try:
        view = _ensure_weekly_view(position.upper())
    except FileNotFoundError:
        return []

    if year is not None:
        rows = _get_conn().execute(
            f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {view} WHERE CAST(year AS INTEGER) = ? ORDER BY wk ASC",
            [year],
        ).fetchall()
    else:
        rows = _get_conn().execute(
            f"SELECT DISTINCT CAST(week AS INTEGER) AS wk FROM {view} ORDER BY wk ASC"
        ).fetchall()

    return [r[0] for r in rows]


def query_player_impact_metrics(
    position: str,
    player_id: str,
    metric_type: str = "surface",
) -> list[dict[str, Any]]:
    """
    Returns performance splits for a specific player from the historical data.
    Supported metric_types: 'surface', 'venue' (indoor/outdoor), 'elevation', 'opponent'.
    """
    view = _ensure_weekly_view(position.upper())
    
    # Map high-level metric types to SQL columns and conditions
    config = {
        "surface": {
            "col": "surface_type",
            "filter": "surface_type IS NOT NULL"
        },
        "venue": {
            "col": "indoor_outdoor",
            "filter": "indoor_outdoor IS NOT NULL"
        },
        "elevation": {
            "col": "CASE WHEN elevation >= 500 THEN 'High' WHEN elevation BETWEEN 100 AND 499 THEN 'Med' ELSE 'Low' END",
            "filter": "elevation IS NOT NULL"
        },
        "opponent": {
            "col": "opponent",
            "filter": "opponent IS NOT NULL"
        }
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
        FROM {view}
        WHERE player_id = ? AND {filter_expr}
        GROUP BY 1
        ORDER BY avg_fpts_ppr DESC
    """
    
    rows = _get_conn().execute(sql, [player_id]).fetchdf()
    return _serialize_rows(rows)


def query_team_defense_stats(position: str) -> list[dict[str, Any]]:
    """Returns average fantasy points allowed by each defense to the given position."""
    view = _ensure_weekly_view(position.upper())
    
    sql = f"""
        SELECT 
            opponent AS defense_team,
            ROUND(AVG(fpts_ppr), 2) AS avg_points_allowed,
            COUNT(*) AS game_count
        FROM {view}
        WHERE opponent IS NOT NULL
        GROUP BY opponent
        ORDER BY avg_points_allowed DESC
    """
    
    rows = _get_conn().execute(sql).fetchdf()
    return _serialize_rows(rows)


# ── Shared Utilities ──────────────────────────────────────────────────────────

def query_player_profile(player_id: str, position: str) -> Optional[dict[str, Any]]:
    """
    Fetch all seasons for a single player by player_id.
    Used for player detail / trend views.
    """
    view = _ensure_view(position.upper())
    rows = _get_conn().execute(
        f"SELECT * FROM {view} WHERE player_id = ? ORDER BY CAST(year AS INTEGER) DESC",
        [player_id],
    ).fetchdf()

    if rows.empty:
        return None

    rows.columns = [c.lower() for c in rows.columns]
    return {"seasons": rows.to_dict(orient="records")}


def invalidate_view(position: str, weekly: bool = False) -> None:
    """
    Drop and re-register a position view. Call this after a pipeline
    run refreshes the underlying file so the new data is picked up.
    """
    suffix = "_weekly" if weekly else ""
    view_name = f"v_{position.lower()}{suffix}"
    try:
        _get_conn().execute(f"DROP VIEW IF EXISTS {view_name}")
    except Exception:
        pass
    _get_registered_views().discard(view_name)
    logger.info("Invalidated DuckDB view: %s", view_name)
