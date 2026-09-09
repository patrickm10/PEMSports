"""
Ranking service — orchestrates data retrieval and caching.

Data access flow:
  1. Check TTL cache (in-memory dict)
  2. On miss: delegate to DuckDB query engine (analytical layer)
  3. Cache the result for the configured TTL

The service layer has no knowledge of file paths or query syntax.
All storage decisions live in backend/data/query_engine.py.

Callers (routes.py) receive plain Python dicts — no DataFrame objects
escape this layer.
"""
import logging
from typing import Any, Optional, List, Dict

from backend.core.cache import cache
from backend.data.query_engine import (
    query_rankings,
    query_seasons,
    query_weekly_rankings,
    query_available_weeks,
    query_player_impact_metrics,
    query_team_defense_stats,
)
from backend.data.ranking_store import stats_generation


def _key(prefix: str, *parts: Any) -> str:
    return ":".join([str(stats_generation()), prefix, *[str(p) for p in parts]])


def invalidate_rankings_cache() -> None:
    cache.clear()

logger = logging.getLogger(__name__)


def get_rankings(
    position: Any,
    year: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Return ranked player records for a position, optionally filtered by year.

    Cache key: "rankings:{position}:{year}:{limit}:{offset}"
    TTL: 300s (default). Invalidated externally when the pipeline refreshes data.

    Pagination note: limit/offset are part of the cache key so different
    pages are cached independently. For the current data size (<2000 rows
    per position), a limit of 200-500 covers all practical use cases.
    """
    cache_key = _key("rankings", position, year, limit, offset)

    
    cached = cache.get(cache_key)
    if cached is not None:

        return cached

    data = query_rankings(position, year=year, limit=limit, offset=offset)
    cache.set(cache_key, data)


    logger.debug(
        "get_rankings(%s, year=%s, limit=%d, offset=%d) → %d records",
        position, year, limit, offset, len(data),
    )
    return data


def get_available_seasons(position: Any) -> List[int]:
    """
    Return descending list of seasons available for a position.
    Cache key: "seasons:{position}"
    """
    cache_key = _key("seasons", position)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    seasons = query_seasons(position)
    cache.set(cache_key, seasons)
    return seasons


def get_weekly_rankings(
    position: Any,
    year: Optional[int] = None,
    week: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Return weekly ranked player records for a position.
    Cache key: "weekly:{position}:{year}:{week}:{limit}:{offset}"
    """
    cache_key = _key("weekly", position, year, week, limit, offset)

    
    cached = cache.get(cache_key)
    if cached is not None:

        return cached

    data = query_weekly_rankings(
        position, year=year, week=week, limit=limit, offset=offset
    )
    cache.set(cache_key, data)


    logger.debug(
        "get_weekly_rankings(%s, year=%s, week=%s) → %d records",
        position, year, week, len(data),
    )
    return data


def get_available_weeks(position: Any, year: Optional[int] = None) -> list[int]:
    """Returns available weeks for a given position and year."""
    cache_key = _key("weeks", position, year or "all")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_available_weeks(position, year=year)
    cache.set(cache_key, data)
    return data


def get_player_impact(position: Any, player_id: str, metric_type: str) -> list[dict[str, Any]]:
    """Returns performance impact metrics for a player."""
    cache_key = _key("impact", player_id, metric_type)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_player_impact_metrics(position, player_id, metric_type)
    cache.set(cache_key, data, ttl=3600)  # 1 hour cache
    return data


def get_defense_stats(position: Any) -> list[dict[str, Any]]:
    """Returns defense-allowed stats for a position."""
    cache_key = _key("defense", position)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = query_team_defense_stats(position)
    cache.set(cache_key, data, ttl=3600)  # 1 hour cache
    return data
