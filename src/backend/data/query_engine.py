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
    PemSportsException,
    QueryEngineError,
    TableMissingError,
)
from backend.utils.team_normalization import normalize_team_abbr

logger = logging.getLogger(__name__)

# Resolve paths — __file__ is under src/backend/data/, so four parents = repo root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = Path(
    os.environ.get("NFL_STATS_DB_PATH", str(_PROJECT_ROOT / "data" / "nfl_stats.db"))
).resolve()

_thread_local = threading.local()
_logged_db_path = False

# ESPN CDN headshot (96x96 crop) — used when players.espn_player_id is present so
# production UI does not depend on shipping gitignored JPEGs with the API image.
_ESPN_HEADSHOT_SQL = (
    "'https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/' "
    "|| CAST(p.espn_player_id AS VARCHAR) || '.png&h=96&w=96&scale=crop'"
)


def _players_table_ready(conn: duckdb.DuckDBPyConnection) -> bool:
    try:
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        if "players" not in tables:
            return False
        cols = {d[0].lower() for d in conn.execute("SELECT * FROM players LIMIT 0").description}
        return "player_id" in cols and "espn_player_id" in cols
    except Exception:  # noqa: BLE001
        return False


def _headshot_select_sql(table_alias: str = "t") -> tuple[str, str]:
    """
    Return (from_clause_suffix, headshot_url_select_expr).

    When `players` is baked with espn_player_id, prefer the ESPN CDN URL so the
    frontend can render photos without a local /headshots file. Otherwise fall
    back to the canonical static path `/headshots/{player_id}.jpg`.
    """
    conn = _get_conn()
    if _players_table_ready(conn):
        join = (
            f" LEFT JOIN players p ON CAST({table_alias}.player_id AS VARCHAR) "
            f"= CAST(p.player_id AS VARCHAR)"
        )
        expr = (
            "COALESCE("
            "CASE WHEN p.espn_player_id IS NOT NULL "
            "AND CAST(p.espn_player_id AS VARCHAR) <> '' "
            f"THEN {_ESPN_HEADSHOT_SQL} END, "
            f"'/headshots/' || CAST({table_alias}.player_id AS VARCHAR) || '.jpg'"
            ") AS headshot_url"
        )
        return join, expr
    return "", f"'/headshots/' || CAST({table_alias}.player_id AS VARCHAR) || '.jpg' AS headshot_url"


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Return a thread-local, read-only connection to the serving database.

    Raises:
        DatabaseUnavailableError: If the baked DB file does not exist.
            We intentionally do NOT fall back to an empty in-memory
            connection, which used to make missing-database errors look
            identical to empty-result responses.
    """
    global _logged_db_path
    if not hasattr(_thread_local, "conn"):
        if not _logged_db_path:
            # Temporary runtime proof: shows the exact DB file in use.
            # This must match the file we query directly and the API responses.
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
        # Normalize team and opponent values to canonical abbreviations (TEAM_MAP) before
        # API response. Seasonal parquets often store abbrs for `team` already; weekly
        # rows may use slug form — same path so weekly and seasonal match.
        for col in ("team", "opp", "opponent", "defense_team"):
            if col in row_dict and row_dict[col] is not None:
                row_dict[col] = normalize_team_abbr(row_dict[col])
        results.append(row_dict)
    return results


def _execute(sql: str, params: list[Any] | None = None, *, context: str) -> list[dict[str, Any]]:
    """Run `sql` with the shared connection, translating duckdb errors.

    `context` is a short label used in log messages (e.g. "qb_weekly").
    """
    def _run() -> list[dict[str, Any]]:
        cursor = _get_conn().execute(sql, params or [])
        return _serialize_rows(cursor)

    try:
        return _run()
    except duckdb.CatalogException as exc:
        logger.warning("Table missing for %s: %s", context, exc)
        raise TableMissingError(f"Table for {context} is not baked.") from exc
    except (duckdb.BinderException, duckdb.ParserException) as exc:
        logger.exception("Query engine SQL error (%s)", context)
        raise QueryEngineError(f"SQL error querying {context}: {exc}") from exc
    except duckdb.IOException as exc:
        # A common local-dev failure mode is rebaking `data/nfl_stats.db` while the
        # server is running. That can invalidate a previously opened DuckDB file
        # handle. We reset the thread-local connection and retry once to recover.
        logger.warning("DuckDB IO error (%s), retrying with fresh connection: %s", context, exc)
        if hasattr(_thread_local, "conn"):
            try:
                delattr(_thread_local, "conn")
            except Exception:
                pass
        try:
            return _run()
        except Exception as exc2:
            logger.exception("DuckDB IO error after retry (%s)", context)
            raise DatabaseUnavailableError(
                f"DuckDB IO failure while querying {context}: {exc2}"
            ) from exc2
    except PemSportsException:
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
        conditions.append("t.year = ?")
        params.append(float(year))

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    join_sql, headshot_expr = _headshot_select_sql("t")

    sql = f"""
    SELECT
        t.*,
        {headshot_expr},
        ROW_NUMBER() OVER (
            PARTITION BY t.year
            ORDER BY t.fpts_ppr DESC NULLS LAST, t.fpts DESC NULLS LAST
        ) AS rank
    FROM {table} t{join_sql}{where_clause}
    ORDER BY t.year DESC, rank ASC
    """

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    return _execute(sql, params, context=table)


def query_seasons(position: str) -> list[int]:
    """
    Return available years for a position (newest first).

    Unions distinct years from both seasonal and weekly tables so the
    metadata contract stays usable if one table regresses (e.g. seasonal
    truncated to a single year while weekly history remains intact).
    """
    pos = position.lower()
    years: set[int] = set()
    found_any_table = False

    for kind in ("seasonal", "weekly"):
        table = f"{pos}_{kind}"
        try:
            rows = _execute(
                f"SELECT DISTINCT CAST(year AS INTEGER) AS yr FROM {table} "
                f"WHERE year IS NOT NULL",
                context=f"{table} (seasons)",
            )
        except TableMissingError:
            continue
        found_any_table = True
        for r in rows:
            yr = r.get("yr")
            if yr is not None:
                years.add(int(yr))

    if not found_any_table:
        raise TableMissingError(f"Table for {pos}_seasonal is not baked.")

    return sorted(years, reverse=True)


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
        conditions.append("t.year = ?")
        params.append(float(year))
    if week is not None:
        conditions.append("t.week = ?")
        params.append(float(week))

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    join_sql, headshot_expr = _headshot_select_sql("t")

    sql = f"""
    SELECT
        t.*,
        {headshot_expr},
        ROW_NUMBER() OVER (
            PARTITION BY t.year, t.week
            ORDER BY t.fpts_ppr DESC NULLS LAST, t.fpts DESC NULLS LAST
        ) AS rank
    FROM {table} t{join_sql}{where_clause}
    ORDER BY t.year DESC, t.week DESC, rank ASC
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


# ── Player Analytics (explicit resources) ─────────────────────────────────────

def _table_columns(table: str) -> set[str]:
    """Return a set of lowercased column names for a baked table."""
    rows = _execute(f"PRAGMA table_info('{table}')", context=f"{table} (schema)")
    cols: set[str] = set()
    for r in rows:
        name = r.get("name")
        if isinstance(name, str):
            cols.add(name.lower())
    return cols


def query_player_search(q: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Cross-position search across all *_seasonal tables.

    Contract: returns schema-stable search hits. Any missing value is null.
    """
    q_norm = (q or "").strip().lower()
    if not q_norm:
        return []

    like = f"%{q_norm}%"
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pos in ("qb", "rb", "wr", "te", "k", "dst"):
        table = f"{pos}_seasonal"
        try:
            cols = _table_columns(table)
        except PemSportsException:
            continue

        # rank may not exist in baked tables; compute a lightweight current-season rank proxy if present.
        rank_expr = "CAST(t.rank AS INTEGER)" if "rank" in cols else "NULL"
        join_sql, headshot_expr = _headshot_select_sql("t")

        sql = f"""
        SELECT
          t.player_id,
          t.player_name,
          '{pos.upper()}' AS position,
          t.team,
          {headshot_expr},
          {rank_expr} AS current_season_rank
        FROM {table} t{join_sql}
        WHERE LOWER(t.player_name) LIKE ?
        ORDER BY t.year DESC
        LIMIT 50
        """
        try:
            rows = _execute(sql, [like], context=f"{table} (player_search)")
        except PemSportsException:
            continue

        for r in rows:
            pid = r.get("player_id")
            if not isinstance(pid, str) or pid in seen:
                continue
            seen.add(pid)

            # Simple match score: prefix gets a bump; keep stable 0..1 range.
            name = (r.get("player_name") or "").lower() if isinstance(r.get("player_name"), str) else ""
            score = 0.6
            if name.startswith(q_norm):
                score = 0.95
            elif q_norm in name:
                score = 0.8

            results.append(
                {
                    "player_id": pid,
                    "player_name": r.get("player_name"),
                    "position": r.get("position"),
                    "team": r.get("team"),
                    "headshot_url": r.get("headshot_url"),
                    "current_season_rank": r.get("current_season_rank"),
                    "match_score": score,
                }
            )

            if len(results) >= limit:
                return results

    return results[:limit]


def query_player_splits(
    *, position: str, player_id: str, dimension: str
) -> dict[str, Any]:
    """Explicit split resource: opponent|stadium|surface|venue."""
    table = f"{position.lower()}_weekly"
    cols = _table_columns(table)

    dim_col_map = {
        "opponent": "opponent",
        "stadium": "stadium_name",
        "surface": "surface_type",
        "venue": "indoor_outdoor",
    }
    dim_col = dim_col_map.get(dimension, "opponent")
    if dim_col not in cols:
        # Contract: still return stable schema, with empty splits.
        return {
            "player_id": player_id,
            "position": position.lower(),
            "dimension": dimension,
            "splits": [],
        }

    avg_yards_expr = "ROUND(AVG(yds), 2)" if "yds" in cols else "NULL"
    avg_tds_expr = "ROUND(AVG(td), 2)" if "td" in cols else "NULL"

    sql = f"""
        SELECT
            {dim_col} AS key,
            COUNT(*) AS games,
            ROUND(AVG(fpts_ppr), 2) AS avg_ppr,
            ROUND(SUM(fpts_ppr), 2) AS total_ppr,
            {avg_yards_expr} AS avg_yards,
            {avg_tds_expr} AS avg_tds
        FROM {table}
        WHERE player_id = ? AND {dim_col} IS NOT NULL
        GROUP BY 1
        ORDER BY avg_ppr DESC NULLS LAST
    """
    rows = _execute(sql, [player_id], context=f"{table} (splits/{dimension})")

    # Ensure schema-stable keys and NaN handling via _serialize_rows already.
    splits = [
        {
            "key": r.get("key"),
            "games": int(r.get("games") or 0),
            "avg_ppr": r.get("avg_ppr"),
            "total_ppr": r.get("total_ppr"),
            "avg_yards": r.get("avg_yards"),
            "avg_tds": r.get("avg_tds"),
        }
        for r in rows
    ]
    return {
        "player_id": player_id,
        "position": position.lower(),
        "dimension": dimension,
        "splits": splits,
    }


def query_player_splits_by_year(
    *, position: str, player_id: str, dimension: str
) -> dict[str, Any]:
    """
    Yearly split resource. Returns rows grouped by (year, dimension key).

    Contract: schema-stable. Keys always present; missing metrics are null.
    """
    table = f"{position.lower()}_weekly"
    cols = _table_columns(table)

    dim_col_map = {
        "opponent": "opponent",
        "stadium": "stadium_name",
        "surface": "surface_type",
        "venue": "indoor_outdoor",
    }
    dim_col = dim_col_map.get(dimension, "opponent")
    if dim_col not in cols:
        return {
            "player_id": player_id,
            "position": position.lower(),
            "dimension": dimension,
            "years": [],
            "rows": [],
        }

    avg_yards_expr = "ROUND(AVG(yds), 2)" if "yds" in cols else "NULL"
    avg_tds_expr = "ROUND(AVG(td), 2)" if "td" in cols else "NULL"

    sql = f"""
        SELECT
            CAST(year AS INTEGER) AS year,
            {dim_col} AS key,
            COUNT(*) AS games,
            ROUND(AVG(fpts_ppr), 2) AS avg_ppr,
            ROUND(SUM(fpts_ppr), 2) AS total_ppr,
            {avg_yards_expr} AS avg_yards,
            {avg_tds_expr} AS avg_tds
        FROM {table}
        WHERE player_id = ? AND {dim_col} IS NOT NULL
        GROUP BY 1, 2
        ORDER BY year DESC, avg_ppr DESC NULLS LAST
    """
    rows = _execute(sql, [player_id], context=f"{table} (splits/{dimension}/by-year)")

    years: list[int] = []
    seen_years: set[int] = set()
    out_rows: list[dict[str, Any]] = []
    for r in rows:
        yr = r.get("year")
        if isinstance(yr, int) and yr not in seen_years:
            years.append(yr)
            seen_years.add(yr)
        out_rows.append(
            {
                "year": yr,
                "key": r.get("key"),
                "games": int(r.get("games") or 0),
                "avg_ppr": r.get("avg_ppr"),
                "total_ppr": r.get("total_ppr"),
                "avg_yards": r.get("avg_yards"),
                "avg_tds": r.get("avg_tds"),
            }
        )

    return {
        "player_id": player_id,
        "position": position.lower(),
        "dimension": dimension,
        "years": years,
        "rows": out_rows,
    }


def query_player_weekly(
    *, position: str, player_id: str, years: list[int] | None = None
) -> dict[str, Any]:
    """Weekly logs across seasons. Returns schema-stable per-week rows."""
    table = f"{position.lower()}_weekly"
    cols = _table_columns(table)

    yards_expr = "CAST(yds AS DOUBLE)" if "yds" in cols else "NULL"
    tds_expr = "CAST(td AS DOUBLE)" if "td" in cols else "NULL"

    conditions: list[str] = ["player_id = ?"]
    params: list[Any] = [player_id]
    if years:
        placeholders = ",".join(["?"] * len(years))
        conditions.append(f"CAST(year AS INTEGER) IN ({placeholders})")
        params.extend([float(y) for y in years])

    where_clause = " AND ".join(conditions)
    sql = f"""
      SELECT
        CAST(year AS INTEGER) AS year,
        CAST(week AS INTEGER) AS week,
        CAST(fpts_ppr AS DOUBLE) AS ppr_fpts,
        CAST(fpts AS DOUBLE) AS fantasy_points,
        {yards_expr} AS yards,
        {tds_expr} AS tds,
        opponent,
        stadium_name,
        surface_type,
        indoor_outdoor,
        NULL AS home_away,
        NULL AS rest_days,
        temp,
        humidity,
        wind,
        weather_impact
      FROM {table}
      WHERE {where_clause}
      ORDER BY year DESC, week ASC
    """
    rows = _execute(sql, params, context=f"{table} (player_weekly)")

    seasons_map: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        yr = r.get("year")
        if not isinstance(yr, int):
            continue
        seasons_map.setdefault(yr, []).append(
            {
                "week": r.get("week"),
                "ppr_fpts": r.get("ppr_fpts"),
                "fantasy_points": r.get("fantasy_points"),
                "yards": r.get("yards"),
                "tds": r.get("tds"),
                "opponent": r.get("opponent"),
                "stadium_name": r.get("stadium_name"),
                "surface_type": r.get("surface_type"),
                "indoor_outdoor": r.get("indoor_outdoor"),
                "home_away": None,
                "rest_days": None,
                "temp": r.get("temp"),
                "humidity": r.get("humidity"),
                "wind": r.get("wind"),
                "weather_impact": r.get("weather_impact"),
            }
        )

    seasons_payload = [
        {"year": yr, "weeks": weeks} for yr, weeks in sorted(seasons_map.items(), reverse=True)
    ]
    return {
        "player_id": player_id,
        "position": position.lower(),
        "metric_keys": ["ppr_fpts", "fantasy_points", "yards", "tds"],
        "seasons": seasons_payload,
    }


def query_player_metadata(*, position: str, player_id: str) -> dict[str, Any]:
    """
    Aggregated context overlays.

    Note: home_away and rest_days are currently not baked; contract requires the
    buckets exist anyway with games=0 and metric values null.
    """
    empty_agg = {"games": 0, "avg_ppr": None, "avg_yards": None, "avg_tds": None}
    rest_buckets = [
        {"bucket": "<6", "aggregate": dict(empty_agg)},
        {"bucket": "6-7", "aggregate": dict(empty_agg)},
        {"bucket": "8-13", "aggregate": dict(empty_agg)},
        {"bucket": "14+", "aggregate": dict(empty_agg)},
    ]
    return {
        "player_id": player_id,
        "position": position.lower(),
        "splits": {
            "home_away": {"home": dict(empty_agg), "away": dict(empty_agg)},
            "rest_buckets": rest_buckets,
            "weather_impact": [],
        },
    }


def invalidate_view(position: str, weekly: bool = False) -> None:
    """NO-OP in persistent mode. Database is updated via bake_db.py."""
    pass
