"""
API v1 routes — player analytics endpoints.

Contract rules (frontend depends on these):
- Schema-stable responses: every documented key is present in every response.
  Missing/unknown values MUST be null (never omitted).
- Explicit resources: one URL per split dimension. No polymorphic ?metric=...
- Backend owns aggregation: frontend does not group-by or heavy-aggregate.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from backend.core.auth import UserProfile
from backend.core.authz import require_player_analytics
from backend.core.limiter import limiter
from backend.data import query_engine

router = APIRouter()


@router.get("/players/search")
@limiter.limit("60/minute")
def player_search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=25),
):
    """Cross-position player search used by the Search modal typeahead."""
    results = query_engine.query_player_search(q=q, limit=limit)
    return JSONResponse(content={"results": results})


@router.get("/players/{player_id}/splits/{dimension}")
@limiter.limit("30/minute")
def player_splits(
    request: Request,
    player_id: str,
    dimension: str = Path(..., pattern="^(opponent|stadium|surface|venue)$"),
    pos: str = Query(..., pattern="^(qb|rb|wr|te|k|dst)$"),
    _user: UserProfile = Depends(require_player_analytics),
):
    """Explicit split resources (one per dimension)."""
    payload = query_engine.query_player_splits(position=pos, player_id=player_id, dimension=dimension)
    return JSONResponse(content=payload)


@router.get("/players/{player_id}/splits/{dimension}/by-year")
@limiter.limit("30/minute")
def player_splits_by_year(
    request: Request,
    player_id: str,
    dimension: str = Path(..., pattern="^(opponent|stadium|surface|venue)$"),
    pos: str = Query(..., pattern="^(qb|rb|wr|te|k|dst)$"),
    _user: UserProfile = Depends(require_player_analytics),
):
    """Yearly split resource: grouped by (year, dimension)."""
    payload = query_engine.query_player_splits_by_year(
        position=pos, player_id=player_id, dimension=dimension
    )
    return JSONResponse(content=payload)


@router.get("/players/{player_id}/weekly")
@limiter.limit("30/minute")
def player_weekly(
    request: Request,
    player_id: str,
    pos: str = Query(..., pattern="^(qb|rb|wr|te|k|dst)$"),
    seasons: Optional[str] = Query(
        default=None,
        description="Optional comma-separated season years (e.g. 2022,2023,2024).",
    ),
    _user: UserProfile = Depends(require_player_analytics),
):
    years: list[int] | None = None
    if seasons:
        parsed: list[int] = []
        for part in seasons.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                parsed.append(int(part))
            except ValueError:
                continue
        years = parsed or None

    payload = query_engine.query_player_weekly(position=pos, player_id=player_id, years=years)
    return JSONResponse(content=payload)


@router.get("/players/{player_id}/metadata")
@limiter.limit("20/minute")
def player_metadata(
    request: Request,
    player_id: str,
    pos: str = Query(..., pattern="^(qb|rb|wr|te|k|dst)$"),
    _user: UserProfile = Depends(require_player_analytics),
):
    payload = query_engine.query_player_metadata(position=pos, player_id=player_id)
    return JSONResponse(content=payload)

