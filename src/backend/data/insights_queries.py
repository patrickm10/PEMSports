"""
DuckDB queries for PEM Insights.

Baseline scope vs observation scope are explicitly separate:
  - Baseline pool: all games for (player_id, year) matching season/year filters only.
  - Observation pool: baseline pool further filtered by week when provided.

Leave-one-out baseline per observation:
  baseline(P, season, week) = AVG(metric) for same player+season excluding current week.
"""

from __future__ import annotations

from typing import Any

from backend.analytics.context_normalization import (
    context_column,
    display_context_value,
    normalize_context_value,
    normalized_context_sql,
)
from backend.analytics.insights_config import (
    DEFAULT_LEADERBOARD_LIMIT,
    DEFAULT_METRIC,
    INSIGHT_POSITIONS,
)
from backend.analytics.insights_math import enrich_insight_row, passes_min_sample
from backend.data.query_engine import _execute, _table_columns


def _metric_column(metric: str) -> str:
    if metric not in ("fpts_ppr", "fpts"):
        raise ValueError(f"Unsupported metric: {metric}")
    return metric


def _season_filter_sql(
    years: list[int] | None, year: int | None, *, table_alias: str | None = None
) -> tuple[str, list[Any]]:
    """Build WHERE clause for season scope (never includes week)."""
    prefix = f"{table_alias}." if table_alias else ""
    params: list[Any] = []
    conditions: list[str] = []

    if years:
        placeholders = ",".join(["?"] * len(years))
        conditions.append(f"CAST({prefix}year AS INTEGER) IN ({placeholders})")
        params.extend([float(y) for y in years])
    elif year is not None:
        conditions.append(f"CAST({prefix}year AS INTEGER) = ?")
        params.append(float(year))

    if not conditions:
        return "", params
    return " AND ".join(conditions), params


def _observation_week_filter_sql(week: int | None, *, table_alias: str | None = None) -> tuple[str, list[Any]]:
    """Week filter applies to observations only, not baseline population."""
    if week is None:
        return "", []
    prefix = f"{table_alias}." if table_alias else ""
    return f"CAST({prefix}week AS INTEGER) = ?", [float(week)]


def _table_has_column(table: str, column: str) -> bool:
    return column.lower() in _table_columns(table)


def _weekly_select_sql(
    *,
    position: str,
    metric: str,
    context: str,
    context_value: str,
    years: list[int] | None,
    year: int | None,
    week: int | None,
) -> tuple[str, list[Any]]:
    """
    Build SQL returning per-observation rows with LOO baseline and context flag.
    """
    context_value = normalize_context_value(context, context_value)
    table = f"{position.lower()}_weekly"
    metric_col = _metric_column(metric)
    raw_ctx_col = context_column(context)

    if not _table_has_column(table, metric_col):
        raise ValueError(f"Metric column {metric_col} missing from {table}")
    if not _table_has_column(table, raw_ctx_col):
        # Stable empty result — column not baked yet (e.g. home_away before rebake).
        return "", []

    norm_ctx_expr = normalized_context_sql(context, f"w.{raw_ctx_col}")
    season_clause, season_params = _season_filter_sql(years, year, table_alias="w")
    week_clause, week_params = _observation_week_filter_sql(week, table_alias="o")

    where_parts = [f"w.{metric_col} IS NOT NULL"]
    if season_clause:
        where_parts.append(season_clause)
    baseline_where = " AND ".join(where_parts)

    obs_parts: list[str] = []
    if week_clause:
        obs_parts.append(week_clause)
    observation_where = " AND ".join(obs_parts) if obs_parts else "TRUE"

    params = list(season_params) + list(week_params) + [context_value]

    sql = f"""
    WITH baseline_pool AS (
        SELECT
            w.player_id,
            w.player_name,
            w.team,
            CAST(w.year AS INTEGER) AS year,
            CAST(w.week AS INTEGER) AS week,
            CAST(w.{metric_col} AS DOUBLE) AS metric_value,
            w.opponent,
            w.stadium_name,
            w.surface_type,
            w.home_away,
            {norm_ctx_expr} AS context_value
        FROM {table} w
        WHERE {baseline_where}
    ),
    with_loo AS (
        SELECT
            *,
            CASE
                WHEN COUNT(*) OVER (PARTITION BY player_id, year) <= 1 THEN NULL
                ELSE (
                    SUM(metric_value) OVER (PARTITION BY player_id, year) - metric_value
                ) / NULLIF(
                    COUNT(*) OVER (PARTITION BY player_id, year) - 1, 0
                )
            END AS loo_baseline,
            metric_value - CASE
                WHEN COUNT(*) OVER (PARTITION BY player_id, year) <= 1 THEN NULL
                ELSE (
                    SUM(metric_value) OVER (PARTITION BY player_id, year) - metric_value
                ) / NULLIF(
                    COUNT(*) OVER (PARTITION BY player_id, year) - 1, 0
                )
            END AS game_delta
        FROM baseline_pool
    ),
    observations AS (
        SELECT *
        FROM with_loo o
        WHERE {observation_where}
          AND context_value = ?
          AND loo_baseline IS NOT NULL
    )
    SELECT
        player_id,
        MAX(player_name) AS player_name,
        MAX(team) AS team,
        COUNT(*) AS sample_size,
        ROUND(AVG(metric_value), 2) AS context_average,
        ROUND(AVG(loo_baseline), 2) AS baseline_value,
        ROUND(AVG(game_delta), 2) AS absolute_delta
    FROM observations
    GROUP BY player_id
    HAVING COUNT(*) >= 1
    """

    return sql, params


def _rank_insights(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        sample_size = int(row.get("sample_size") or 0)
        if not passes_min_sample(sample_size):
            continue
        enriched.append(enrich_insight_row(dict(row)))

    enriched.sort(
        key=lambda r: (
            r.get("insight_score") is None,
            -(r.get("insight_score") or 0),
            -(r.get("sample_size") or 0),
        )
    )
    return enriched[:limit]


def query_insights_leaderboard(
    *,
    position: str,
    context: str,
    context_value: str,
    metric: str = DEFAULT_METRIC,
    years: list[int] | None = None,
    year: int | None = None,
    week: int | None = None,
    limit: int = DEFAULT_LEADERBOARD_LIMIT,
) -> dict[str, Any]:
    """
    Return insights leaderboard for one position, or grouped by position when position=all.
    """
    pos = position.lower()
    base_meta = {
        "context": context,
        "context_value": context_value,
        "metric": metric,
        "year": year,
        "week": week,
        "years": years,
    }

    if pos == "all":
        groups: list[dict[str, Any]] = []
        for p in INSIGHT_POSITIONS:
            group = _query_single_position_leaderboard(
                position=p,
                context=context,
                context_value=context_value,
                metric=metric,
                years=years,
                year=year,
                week=week,
                limit=limit,
            )
            groups.append(
                {
                    "position": p,
                    "insights": group.get("insights", []),
                }
            )
        return {
            "position": "all",
            **base_meta,
            "groups": groups,
            "insights": None,
        }

    if pos not in INSIGHT_POSITIONS:
        raise ValueError(f"Unsupported position: {position}")

    result = _query_single_position_leaderboard(
        position=pos,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
        limit=limit,
    )
    return {
        "position": pos,
        **base_meta,
        "groups": None,
        **result,
    }


def _query_single_position_leaderboard(
    *,
    position: str,
    context: str,
    context_value: str,
    metric: str,
    years: list[int] | None,
    year: int | None,
    week: int | None,
    limit: int,
) -> dict[str, Any]:
    sql, params = _weekly_select_sql(
        position=position,
        metric=metric,
        context=context,
        context_value=context_value,
        years=years,
        year=year,
        week=week,
    )
    if not sql:
        return {"insights": []}

    rows = _execute(sql, params, context=f"{position}_weekly (insights)")
    for row in rows:
        row["position"] = position.lower()

    return {"insights": _rank_insights(rows, limit)}


def query_insights_player_detail(
    *,
    position: str,
    player_id: str,
    context: str,
    context_value: str,
    metric: str = DEFAULT_METRIC,
    years: list[int] | None = None,
    year: int | None = None,
    week: int | None = None,
) -> dict[str, Any]:
    """Weekly observations for one player with LOO baselines and relative change."""
    pos = position.lower()
    if pos not in INSIGHT_POSITIONS:
        raise ValueError(f"Unsupported position: {position}")

    context_value = normalize_context_value(context, context_value)

    table = f"{pos}_weekly"
    metric_col = _metric_column(metric)
    raw_ctx_col = context_column(context)

    if not _table_has_column(table, metric_col):
        return _empty_player_detail(pos, player_id, context, context_value, metric)

    if not _table_has_column(table, raw_ctx_col):
        return _empty_player_detail(pos, player_id, context, context_value, metric)

    norm_ctx_expr = normalized_context_sql(context, f"w.{raw_ctx_col}")
    season_clause, season_params = _season_filter_sql(years, year, table_alias="w")
    week_clause, week_params = _observation_week_filter_sql(week, table_alias="o")

    where_parts = ["w.player_id = ?", f"w.{metric_col} IS NOT NULL"]
    params: list[Any] = [player_id]
    if season_clause:
        where_parts.append(season_clause)
        params.extend(season_params)
    baseline_where = " AND ".join(where_parts)

    obs_parts: list[str] = []
    if week_clause:
        obs_parts.append(week_clause)
    observation_where = " AND ".join(obs_parts) if obs_parts else "TRUE"

    sql = f"""
    WITH baseline_pool AS (
        SELECT
            w.player_id,
            w.player_name,
            w.team,
            CAST(w.year AS INTEGER) AS season,
            CAST(w.week AS INTEGER) AS week,
            CAST(w.{metric_col} AS DOUBLE) AS metric_value,
            w.opponent,
            w.stadium_name,
            w.surface_type,
            w.home_away,
            {norm_ctx_expr} AS context_value
        FROM {table} w
        WHERE {baseline_where}
    ),
    with_loo AS (
        SELECT
            *,
            CASE
                WHEN COUNT(*) OVER (PARTITION BY player_id, season) <= 1 THEN NULL
                ELSE (
                    SUM(metric_value) OVER (PARTITION BY player_id, season) - metric_value
                ) / NULLIF(
                    COUNT(*) OVER (PARTITION BY player_id, season) - 1, 0
                )
            END AS season_baseline,
            CASE
                WHEN context_value = ? THEN TRUE ELSE FALSE
            END AS in_context
        FROM baseline_pool
    ),
    observations AS (
        SELECT *
        FROM with_loo o
        WHERE {observation_where}
    )
    SELECT
        season,
        week,
        opponent,
        stadium_name,
        surface_type,
        home_away,
        ROUND(metric_value, 2) AS fantasy_points,
        ROUND(season_baseline, 2) AS season_baseline,
        CASE
            WHEN season_baseline IS NULL OR season_baseline = 0 THEN NULL
            ELSE ROUND(100.0 * (metric_value - season_baseline) / season_baseline, 2)
        END AS relative_change_pct,
        in_context,
        player_name,
        team
    FROM observations
    ORDER BY season DESC, week ASC
    """

    detail_params = list(params) + [context_value] + list(week_params)
    rows = _execute(sql, detail_params, context=f"{table} (insights/player)")

    context_rows = [r for r in rows if r.get("in_context")]
    sample_size = len(context_rows)

    summary: dict[str, Any] = {
        "player_id": player_id,
        "position": pos,
        "context": context,
        "context_value": context_value,
        "metric": metric,
        "sample_size": sample_size,
        "baseline_value": None,
        "context_average": None,
        "absolute_delta": None,
        "relative_delta_pct": None,
        "sample_strength": None,
        "insight_score": None,
    }

    if context_rows and sample_size > 0:
        baselines = [r["season_baseline"] for r in context_rows if r.get("season_baseline") is not None]
        metrics = [r["fantasy_points"] for r in context_rows if r.get("fantasy_points") is not None]
        if baselines and metrics:
            context_avg = round(sum(metrics) / len(metrics), 2)
            baseline_avg = round(sum(baselines) / len(baselines), 2)
            abs_delta = round(context_avg - baseline_avg, 2)
            summary_row = enrich_insight_row(
                {
                    "sample_size": sample_size,
                    "context_average": context_avg,
                    "baseline_value": baseline_avg,
                    "absolute_delta": abs_delta,
                }
            )
            summary.update(
                {
                    "baseline_value": summary_row.get("baseline_value"),
                    "context_average": summary_row.get("context_average"),
                    "absolute_delta": summary_row.get("absolute_delta"),
                    "relative_delta_pct": summary_row.get("relative_delta_pct"),
                    "sample_strength": summary_row.get("sample_strength"),
                    "insight_score": summary_row.get("insight_score"),
                }
            )

    if rows:
        summary["player_name"] = rows[0].get("player_name")
        summary["team"] = rows[0].get("team")

    return {
        "player_id": player_id,
        "position": pos,
        "context": context,
        "context_value": context_value,
        "metric": metric,
        "summary": summary,
        "observations": rows,
    }


def _empty_player_detail(
    position: str,
    player_id: str,
    context: str,
    context_value: str,
    metric: str,
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "position": position,
        "context": context,
        "context_value": context_value,
        "metric": metric,
        "summary": {
            "player_id": player_id,
            "position": position,
            "context": context,
            "context_value": context_value,
            "metric": metric,
            "sample_size": 0,
            "baseline_value": None,
            "context_average": None,
            "absolute_delta": None,
            "relative_delta_pct": None,
            "sample_strength": None,
            "insight_score": None,
        },
        "observations": [],
    }


def query_insights_context_values(
    *,
    position: str,
    context: str,
    years: list[int] | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """List distinct normalized context values available for a position."""
    pos = position.lower()
    positions = list(INSIGHT_POSITIONS) if pos == "all" else [pos]
    values: set[str] = set()

    raw_ctx_col = context_column(context)

    for p in positions:
        table = f"{p}_weekly"
        if not _table_has_column(table, raw_ctx_col):
            continue
        norm_expr = normalized_context_sql(context, raw_ctx_col)
        season_clause, season_params = _season_filter_sql(years, year)
        where = f"{raw_ctx_col} IS NOT NULL"
        if season_clause:
            where = f"{where} AND {season_clause}"

        sql = f"""
            SELECT DISTINCT {norm_expr} AS ctx_val
            FROM {table}
            WHERE {where}
              AND {norm_expr} IS NOT NULL
            ORDER BY ctx_val
        """
        rows = _execute(sql, season_params, context=f"{table} (insights/contexts)")
        for r in rows:
            val = r.get("ctx_val")
            if val:
                values.add(display_context_value(context, str(val)))

    return {
        "position": pos,
        "context": context,
        "values": sorted(values),
    }
