"""
Insights service — cache orchestration over insights_queries.
"""

from __future__ import annotations

from typing import Any

from backend.analytics.context_normalization import normalize_context_value
from backend.analytics.insights_config import DEFAULT_LEADERBOARD_LIMIT, DEFAULT_METRIC
from backend.core.cache import cache
from backend.data.insights_queries import (
    query_insights_context_values,
    query_insights_leaderboard,
    query_insights_player_detail,
)


def _cache_key(prefix: str, **parts: Any) -> str:
    ordered = ":".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))
    return f"{prefix}:{ordered}"


def get_insights_leaderboard(
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
    context_value = normalize_context_value(context, context_value)
    cache_key = _cache_key(
        "insights",
        position=position,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
        limit=limit,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_insights_leaderboard(
        position=position,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
        limit=limit,
    )
    cache.set(cache_key, data)
    return data


def get_insights_player_detail(
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
    context_value = normalize_context_value(context, context_value)
    cache_key = _cache_key(
        "insights_player",
        position=position,
        player_id=player_id,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_insights_player_detail(
        position=position,
        player_id=player_id,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
    )
    cache.set(cache_key, data)
    return data


def get_insights_context_values(
    *,
    position: str,
    context: str,
    years: list[int] | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    cache_key = _cache_key(
        "insights_contexts",
        position=position,
        context=context,
        years=years,
        year=year,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_insights_context_values(
        position=position,
        context=context,
        years=years,
        year=year,
    )
    cache.set(cache_key, data)
    return data
