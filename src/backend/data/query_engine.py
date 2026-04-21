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

import json
import logging
import math
import os
import threading
from pathlib import Path
from typing import Any, Optional

import duckdb

from backend.core.exceptions import (
    DatabaseUnavailableError,
    InvalidParameterError,
    NFLStatsException,
    QueryEngineError,
    TableMissingError,
)

logger = logging.getLogger(__name__)

# Mirrors scripts/bake_db.py POSITIONS — used to validate dynamic table names.
_ALLOWED_PROFILE_POSITIONS = frozenset({"qb", "rb", "wr", "te", "k", "dst"})

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
    year: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Analytical splits for performance metrics (optionally scoped to one season)."""
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

    year_clause = " AND year = ?" if year is not None else ""
    params: list[Any] = [player_id]
    if year is not None:
        params.append(float(year))

    sql = f"""
        SELECT
            {cfg['col']} AS metric_label,
            ROUND(AVG(fpts), 2) AS avg_fpts,
            ROUND(AVG(fpts_ppr), 2) AS avg_fpts_ppr,
            COUNT(*) AS games_played
        FROM {table}
        WHERE player_id = ?{year_clause} AND {cfg['filter']}
        GROUP BY 1
        ORDER BY avg_fpts_ppr DESC
    """

    return _execute(sql, params, context=f"{table} (impact/{metric_type})")


_ELEVATION_BAND_SQL = (
    "CASE WHEN elevation >= 500 THEN 'High' "
    "WHEN elevation BETWEEN 100 AND 499 THEN 'Med' "
    "ELSE 'Low' END"
)


def query_player_weekly_facets(
    position: str,
    player_id: str,
    year: int,
) -> dict[str, Any]:
    """Distinct matchup / environment values for filter dropdowns (one season)."""
    pos = position.lower().strip()
    if pos not in _ALLOWED_PROFILE_POSITIONS:
        raise QueryEngineError(f"Invalid position for facets query: {position!r}")

    table = f"{pos}_weekly"
    yr = float(year)

    opponents = _execute(
        f"""
        SELECT DISTINCT TRIM(CAST(opponent AS VARCHAR)) AS v
        FROM {table}
        WHERE player_id = ? AND year = ? AND opponent IS NOT NULL AND TRIM(CAST(opponent AS VARCHAR)) <> ''
        ORDER BY 1
        """,
        [player_id, yr],
        context=f"{table} (facets/opponents)",
    )
    venues = _execute(
        f"""
        SELECT DISTINCT TRIM(CAST(indoor_outdoor AS VARCHAR)) AS v
        FROM {table}
        WHERE player_id = ? AND year = ? AND indoor_outdoor IS NOT NULL
        ORDER BY 1
        """,
        [player_id, yr],
        context=f"{table} (facets/venues)",
    )
    surfaces = _execute(
        f"""
        SELECT DISTINCT TRIM(CAST(surface_type AS VARCHAR)) AS v
        FROM {table}
        WHERE player_id = ? AND year = ? AND surface_type IS NOT NULL
        ORDER BY 1
        """,
        [player_id, yr],
        context=f"{table} (facets/surfaces)",
    )
    bands = _execute(
        f"""
        SELECT DISTINCT {_ELEVATION_BAND_SQL} AS v
        FROM {table}
        WHERE player_id = ? AND year = ? AND elevation IS NOT NULL
        ORDER BY 1
        """,
        [player_id, yr],
        context=f"{table} (facets/elevation)",
    )

    return {
        "opponents": [r["v"] for r in opponents if r.get("v")],
        "indoor_outdoor": [r["v"] for r in venues if r.get("v")],
        "surface_type": [r["v"] for r in surfaces if r.get("v")],
        "elevation_band": [r["v"] for r in bands if r.get("v")],
    }


def query_player_conditional_split(
    position: str,
    player_id: str,
    year: int,
    *,
    opponent: Optional[str] = None,
    indoor_outdoor: Optional[str] = None,
    surface_type: Optional[str] = None,
    elevation_band: Optional[str] = None,
) -> dict[str, Any]:
    """Baseline vs. AND-filtered weekly sample for situational intelligence (one season)."""
    pos = position.lower().strip()
    if pos not in _ALLOWED_PROFILE_POSITIONS:
        raise QueryEngineError(f"Invalid position for split query: {position!r}")

    filters = [opponent, indoor_outdoor, surface_type, elevation_band]
    if not any(f is not None and str(f).strip() != "" for f in filters):
        raise InvalidParameterError(
            "At least one of opponent, indoor_outdoor, surface_type, or elevation_band is required."
        )

    table = f"{pos}_weekly"
    yr = float(year)

    base_where = "player_id = ? AND year = ?"
    base_params: list[Any] = [player_id, yr]

    extra: list[str] = []
    extra_params: list[Any] = []
    if opponent is not None and str(opponent).strip() != "":
        extra.append("TRIM(CAST(opponent AS VARCHAR)) = TRIM(?)")
        extra_params.append(opponent)
    if indoor_outdoor is not None and str(indoor_outdoor).strip() != "":
        extra.append("TRIM(CAST(indoor_outdoor AS VARCHAR)) = TRIM(?)")
        extra_params.append(indoor_outdoor)
    if surface_type is not None and str(surface_type).strip() != "":
        extra.append("TRIM(CAST(surface_type AS VARCHAR)) = TRIM(?)")
        extra_params.append(surface_type)
    if elevation_band is not None and str(elevation_band).strip() != "":
        extra.append(f"{_ELEVATION_BAND_SQL} = TRIM(?)")
        extra_params.append(elevation_band)

    agg_sql = f"""
        SELECT
            COUNT(*)::INTEGER AS games,
            ROUND(AVG(fpts_ppr), 4) AS avg_fpts_ppr,
            ROUND(AVG(COALESCE(yds, 0) + COALESCE(rush_yds, 0)), 2) AS avg_scrimmage_yds
        FROM {table}
        WHERE {{where}}
    """

    baseline_rows = _execute(
        agg_sql.format(where=base_where),
        base_params,
        context=f"{table} (split/baseline)",
    )
    cond_where = base_where + (" AND " + " AND ".join(extra) if extra else "")
    cond_params = base_params + extra_params
    filtered_rows = _execute(
        agg_sql.format(where=cond_where),
        cond_params,
        context=f"{table} (split/conditional)",
    )

    if not baseline_rows:
        return {}

    b = baseline_rows[0]
    f = filtered_rows[0] if filtered_rows else {"games": 0}

    def _num(row: dict[str, Any], key: str) -> Optional[float]:
        v = row.get(key)
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    b_games = int(_num(b, "games") or 0)
    f_games = int(_num(f, "games") or 0)
    b_ppr = _num(b, "avg_fpts_ppr")
    f_ppr = _num(f, "avg_fpts_ppr")
    b_yds = _num(b, "avg_scrimmage_yds")
    f_yds = _num(f, "avg_scrimmage_yds")

    def _pct(baseline: Optional[float], sample: Optional[float]) -> Optional[float]:
        if baseline is None or sample is None:
            return None
        if baseline == 0:
            return None
        return round((sample - baseline) / baseline * 100.0, 2)

    return {
        "year": int(year),
        "filters": {
            "opponent": opponent,
            "indoor_outdoor": indoor_outdoor,
            "surface_type": surface_type,
            "elevation_band": elevation_band,
        },
        "baseline": {
            "games": b_games,
            "avg_fpts_ppr": b_ppr,
            "avg_scrimmage_yds": b_yds,
        },
        "conditional": {
            "games": f_games,
            "avg_fpts_ppr": f_ppr,
            "avg_scrimmage_yds": f_yds,
        },
        "delta_pct": {
            "fpts_ppr": _pct(b_ppr, f_ppr),
            "scrimmage_yds": _pct(b_yds, f_yds),
        },
    }


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


def get_player_full_profile(
    player_id: str,
    year: int,
    position: str,
) -> Optional[dict[str, Any]]:
    """Single-query seasonal row (with rank) + weekly game logs for one season.

    Tables are `{position}_seasonal` and `{position}_weekly` (bake_db). Rank uses
    the same window as `query_rankings`. Weekly rows are ordered by week.

    Returns:
        ``{"season": dict, "weekly_games": list[dict], "season_history": list[dict]}``
        or ``None`` if the player has no seasonal row for that year.

        ``season_history`` is every seasonal row for ``player_id`` (all years),
        each with ``rank`` for that year, newest year first.
    """
    pos = position.lower().strip()
    if pos not in _ALLOWED_PROFILE_POSITIONS:
        raise QueryEngineError(f"Invalid position for profile query: {position!r}")

    st = f"{pos}_seasonal"
    wt = f"{pos}_weekly"
    yr = float(year)

    sql = f"""
    WITH ranked_season AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY year
                ORDER BY fpts_ppr DESC NULLS LAST, fpts DESC NULLS LAST
            ) AS rank
        FROM {st}
        WHERE year = ?
    ),
    season_row AS (
        SELECT * FROM ranked_season WHERE player_id = ?
    ),
    week_rows AS (
        SELECT * FROM {wt}
        WHERE player_id = ? AND year = ?
    ),
    week_sorted AS (
        SELECT * FROM week_rows ORDER BY week
    ),
    ranked_all_years AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY year
                ORDER BY fpts_ppr DESC NULLS LAST, fpts DESC NULLS LAST
            ) AS rank
        FROM {st}
        WHERE player_id = ?
    ),
    all_seasons_sorted AS (
        SELECT * FROM ranked_all_years ORDER BY year DESC
    )
    SELECT
        (SELECT json(s) FROM season_row s LIMIT 1) AS season_json,
        COALESCE(
            (SELECT json_group_array(json(t)) FROM week_sorted t),
            CAST('[]' AS JSON)
        ) AS weekly_json,
        COALESCE(
            (SELECT json_group_array(json(t)) FROM all_seasons_sorted t),
            CAST('[]' AS JSON)
        ) AS season_history_json
    """

    rows = _execute(
        sql,
        [yr, player_id, player_id, yr, player_id],
        context=f"{st}+{wt} (full_profile)",
    )
    if not rows:
        return None

    raw_season = rows[0].get("season_json")
    raw_weekly = rows[0].get("weekly_json")
    raw_history = rows[0].get("season_history_json")
    if raw_season is None or (isinstance(raw_season, str) and raw_season in ("", "null")):
        return None

    season_obj: Any
    if isinstance(raw_season, str):
        season_obj = json.loads(raw_season)
    else:
        season_obj = raw_season

    weekly_obj: Any
    if isinstance(raw_weekly, str):
        weekly_obj = json.loads(raw_weekly)
    else:
        weekly_obj = raw_weekly

    if not isinstance(season_obj, dict):
        raise QueryEngineError("Unexpected seasonal payload shape from profile query.")

    weekly_list = weekly_obj if isinstance(weekly_obj, list) else list(weekly_obj or [])

    history_obj: Any
    if isinstance(raw_history, str):
        history_obj = json.loads(raw_history)
    else:
        history_obj = raw_history
    history_list = history_obj if isinstance(history_obj, list) else list(history_obj or [])

    # Normalize NaN from JSON (should be rare) for consistency with _serialize_rows
    def _nan_fix(obj: Any) -> Any:
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _nan_fix(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_nan_fix(v) for v in obj]
        return obj

    return {
        "season": _nan_fix(season_obj),
        "weekly_games": _nan_fix(weekly_list),
        "season_history": _nan_fix(history_list),
    }


def invalidate_view(position: str, weekly: bool = False) -> None:
    """NO-OP in persistent mode. Database is updated via bake_db.py."""
    pass
