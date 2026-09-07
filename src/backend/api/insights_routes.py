"""
API v1 routes — PEM Insights endpoints.

Backend owns all analytical derivation; frontend receives pre-computed insights.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from backend.analytics.context_normalization import SUPPORTED_CONTEXTS
from backend.analytics.insights_config import (
    DEFAULT_LEADERBOARD_LIMIT,
    DEFAULT_METRIC,
    INSIGHT_POSITIONS,
    SUPPORTED_METRICS,
)
from backend.core.limiter import limiter
from backend.services.insights_service import (
    get_insights_context_values,
    get_insights_leaderboard,
    get_insights_player_detail,
)

router = APIRouter()

_POSITION_PATTERN = "^(all|qb|rb|wr|te)$"
_CONTEXT_PATTERN = "^(" + "|".join(SUPPORTED_CONTEXTS) + ")$"
_METRIC_PATTERN = "^(" + "|".join(SUPPORTED_METRICS) + ")$"


def _parse_seasons(seasons: Optional[str]) -> list[int] | None:
    if not seasons:
        return None
    parsed: list[int] = []
    for part in seasons.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            parsed.append(int(part))
        except ValueError:
            continue
    return parsed or None


@router.get("/insights")
@limiter.limit("60/minute")
def api_get_insights(
    request: Request,
    position: str = Query(..., pattern=_POSITION_PATTERN),
    context: str = Query(..., pattern=_CONTEXT_PATTERN),
    context_value: str = Query(..., min_length=1),
    metric: str = Query(default=DEFAULT_METRIC, pattern=_METRIC_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    week: Optional[int] = Query(default=None, ge=1, le=22),
    seasons: Optional[str] = Query(
        default=None,
        description="Optional comma-separated season years (e.g. 2022,2023,2024).",
    ),
    limit: int = Query(default=DEFAULT_LEADERBOARD_LIMIT, ge=1, le=50),
):
    """Relative performance leaderboard for a position and context."""
    years = _parse_seasons(seasons)
    payload = get_insights_leaderboard(
        position=position,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
        limit=limit,
    )
    return JSONResponse(content=payload)


@router.get("/insights/contexts")
@limiter.limit("60/minute")
def api_get_insights_contexts(
    request: Request,
    position: str = Query(..., pattern=_POSITION_PATTERN),
    context: str = Query(..., pattern=_CONTEXT_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    seasons: Optional[str] = Query(default=None),
):
    """Distinct normalized context values for UI selectors."""
    years = _parse_seasons(seasons)
    payload = get_insights_context_values(
        position=position,
        context=context,
        years=years,
        year=year,
    )
    return JSONResponse(content=payload)


@router.get("/insights/player/{player_id}")
@limiter.limit("30/minute")
def api_get_insights_player(
    request: Request,
    player_id: str,
    position: str = Query(..., pattern="^(" + "|".join(INSIGHT_POSITIONS) + ")$"),
    context: str = Query(..., pattern=_CONTEXT_PATTERN),
    context_value: str = Query(..., min_length=1),
    metric: str = Query(default=DEFAULT_METRIC, pattern=_METRIC_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    week: Optional[int] = Query(default=None, ge=1, le=22),
    seasons: Optional[str] = Query(default=None),
):
    """Weekly observations and summary for one player in a context."""
    years = _parse_seasons(seasons)
    payload = get_insights_player_detail(
        position=position,
        player_id=player_id,
        context=context,
        context_value=context_value,
        metric=metric,
        years=years,
        year=year,
        week=week,
    )
    return JSONResponse(content=payload)
