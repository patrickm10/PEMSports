"""
API v1 routes — player analytics endpoints.

Contract rules:
- Search returns `{ "results": [...] }` with schema-stable hits.
- Split dimensions are validated at the boundary; invalid values → 422.
- `pos` is required on per-player resources and normalized to lowercase
  before delegating to the query engine.
- Domain errors bubble to the global handler in `main.py`.
"""
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Query, Request

from backend.core.limiter import limiter
from backend.data.query_engine import (
    query_player_metadata,
    query_player_search,
    query_player_splits,
    query_player_splits_by_year,
    query_player_weekly,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_seasons(raw: Optional[str]) -> Optional[List[int]]:
    if not raw or not raw.strip():
        return None
    years: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        years.append(int(part))
    return years or None


@router.get("/players/search")
@limiter.limit("60/minute")
def api_player_search(
    request: Request,
    q: str = Query(default="", description="Player name search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results to return"),
):
    """Cross-position player search."""
    results = query_player_search(q, limit=limit)
    return {"results": results}


@router.get("/players/{player_id}/splits/{dimension}")
@limiter.limit("60/minute")
def api_player_splits(
    request: Request,
    player_id: str,
    dimension: Literal["opponent", "stadium", "surface", "venue"],
    pos: str = Query(..., description="Player position (QB, RB, WR, TE, K, DST)"),
):
    """Performance splits for a player by dimension."""
    return query_player_splits(position=pos, player_id=player_id, dimension=dimension)


@router.get("/players/{player_id}/splits/{dimension}/by-year")
@limiter.limit("60/minute")
def api_player_splits_by_year(
    request: Request,
    player_id: str,
    dimension: Literal["opponent", "stadium", "surface", "venue"],
    pos: str = Query(..., description="Player position (QB, RB, WR, TE, K, DST)"),
):
    """Yearly performance splits for a player by dimension."""
    return query_player_splits_by_year(
        position=pos, player_id=player_id, dimension=dimension
    )


@router.get("/players/{player_id}/weekly")
@limiter.limit("60/minute")
def api_player_weekly(
    request: Request,
    player_id: str,
    pos: str = Query(..., description="Player position (QB, RB, WR, TE, K, DST)"),
    seasons: Optional[str] = Query(
        default=None,
        description="Comma-separated season years to filter (e.g. 2023,2024)",
    ),
):
    """Weekly game logs for a player across seasons."""
    return query_player_weekly(
        position=pos,
        player_id=player_id,
        years=_parse_seasons(seasons),
    )


@router.get("/players/{player_id}/metadata")
@limiter.limit("30/minute")
def api_player_metadata(
    request: Request,
    player_id: str,
    pos: str = Query(..., description="Player position (QB, RB, WR, TE, K, DST)"),
):
    """Aggregated context overlays for a player."""
    return query_player_metadata(position=pos, player_id=player_id)
