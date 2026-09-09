"""
API v1 routes — rankings endpoints.

Contract rules:
- Position is allowlisted at the FastAPI Path/Query boundary
  (`qb|rb|wr|te|k|dst`). Invalid positions return 422, not 400.
- Year is bounded to [2018, 2030]. Values outside throw a 422.
- Pagination defaults: limit=200, offset=0. Max limit=1000.
- Response shape is stable — adding fields is not a breaking change,
  removing fields is.

Error handling:
- Domain errors (`NFLStatsException` subclasses) bubble up and are mapped
  by the global handler in `main.py`. Routes should NOT swallow them
  with `try/except Exception`. A broad handler here would mask a
  `TableMissingError` as a 500.
"""
import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from backend.core.exceptions import NoDataForFilterError
from backend.core.limiter import limiter
from backend.services.ranking_service import (
    get_available_seasons,
    get_available_weeks,
    get_defense_stats,
    get_player_impact,
    get_rankings,
    get_weekly_rankings,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_POSITION_PATTERN = "(?i)^(qb|rb|wr|te|k|dst)$"


@router.get("/debug-test")
def debug_test():
    return {"status": "ok", "message": "Router is alive"}


@router.get("/rankings/{pos}")
@limiter.limit("60/minute")
def api_get_rankings(
    request: Request,
    pos: str = Path(..., pattern=_POSITION_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030, description="Filter to a specific season year"),
    limit: int = Query(default=200, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip for pagination"),
):
    """Returns fantasy rankings for a specific position."""
    data = get_rankings(pos, year=year, limit=limit, offset=offset)
    return JSONResponse(content=data)


@router.get("/rankings/{pos}/seasons")
@limiter.limit("30/minute")
def api_get_seasons(request: Request, pos: str = Path(..., pattern=_POSITION_PATTERN)):
    """Returns available season years for the given position, most recent first."""
    return get_available_seasons(pos)


@router.get("/rankings/{pos}/weekly")
@limiter.limit("60/minute")
def api_get_weekly_rankings(
    request: Request,
    pos: str = Path(..., pattern=_POSITION_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    week: Optional[int] = Query(default=None, ge=1, le=18),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Returns weekly fantasy rankings for a specific position."""
    data = get_weekly_rankings(pos, year=year, week=week, limit=limit, offset=offset)
    return JSONResponse(content=data)


@router.get("/rankings/{pos}/weeks")
@limiter.limit("30/minute")
def get_position_weeks(
    request: Request,
    pos: str = Path(..., pattern=_POSITION_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
):
    """Returns available weeks for the given position, optionally filtered by year."""
    return get_available_weeks(pos, year=year)


@router.get("/weekly-rankings")
@limiter.limit("60/minute")
def get_all_weekly_rankings(
    request: Request,
    pos: str = Query(..., pattern=_POSITION_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    week: Optional[int] = Query(default=None, ge=1, le=18),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Alias for /rankings/{pos}/weekly."""
    data = get_weekly_rankings(pos, year=year, week=week, limit=limit, offset=offset)
    return JSONResponse(content=data)


@router.get("/rankings/{pos}/impact/{player_id}")
@limiter.limit("30/minute")
def get_player_impact_metrics(
    request: Request,
    pos: str = Path(..., pattern=_POSITION_PATTERN),
    player_id: str = Path(...),
    metric: str = Query(default="surface", description="Analysis type: surface, venue, elevation, opponent"),
):
    """Returns historical performance splits for a player based on external factors."""
    return get_player_impact(pos, player_id, metric)


@router.get("/rankings/{pos}/defense")
@limiter.limit("20/minute")
def api_get_defense_stats_analytics(request: Request, pos: str = Path(..., pattern=_POSITION_PATTERN)):
    """Returns ranking of NFL defenses based on fantasy points allowed to the given position."""
    return get_defense_stats(pos)


@router.get(
    "/rankings/{pos}/csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
@limiter.limit("10/minute")
def get_player_rankings_csv(
    request: Request,
    pos: str = Path(..., pattern=_POSITION_PATTERN),
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
):
    """Returns rankings as a downloadable CSV file."""
    data = get_rankings(pos, year=year, limit=1000, offset=0)

    if not data:
        raise NoDataForFilterError("No data available for export.")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    filename = f"nfl_{pos}_{year or 'all'}_rankings.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
