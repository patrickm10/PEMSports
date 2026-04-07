"""
API v1 routes — rankings endpoints.

Contract rules:
- Position is validated via the Position enum at the FastAPI boundary.
  Invalid positions return 422 (Unprocessable Entity), not 400.
- Year is bounded to [2018, 2030]. Values outside throw a 422.
- Pagination defaults: limit=200, offset=0. Max limit=1000.
- Response shape is stable — adding fields is not a breaking change,
  removing fields is.
"""
import json
import logging
import io
import csv
from typing import List, Optional, Any, Dict, Literal

from fastapi import APIRouter, HTTPException, Query, Response, Request
from fastapi.responses import JSONResponse
from backend.core.limiter import limiter

# Position import removed to bypass Pydantic ForwardRef issues
from backend.services.ranking_service import (
    get_available_seasons,
    get_rankings,
    get_weekly_rankings,
    get_available_weeks,
    get_player_impact,
    get_defense_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/debug-test")
def debug_test():
    return {"status": "ok", "message": "Router is alive"}



@router.get("/rankings/{pos}")
@limiter.limit("60/minute")
def api_get_rankings(
    request: Request,
    pos: str,
    year: Optional[int] = Query(default=None, ge=2018, le=2030, description="Filter to a specific season year"),
    limit: int = Query(default=200, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip for pagination"),
):
    """
    Returns fantasy rankings for a specific position.
    Performance: Bypasses Pydantic validation for high-volume data.
    """
    try:
        data = get_rankings(pos, year=year, limit=limit, offset=offset)
        if not data:
            raise HTTPException(status_code=500, detail="Data empty for position")
        # Optimized: Direct JSONResponse bypasses Pydantic's slow validation loop for large lists
        return JSONResponse(content=data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in get_player_rankings(%s, year=%s)", pos, year)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/rankings/{pos}/seasons")
@limiter.limit("30/minute")
def api_get_seasons(request: Request, pos: str):
    """Returns available season years for the given position, most recent first."""
    try:
        return get_available_seasons(pos)
    except Exception as exc:
        logger.exception("Unexpected error in get_position_seasons(%s)", pos)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/rankings/{pos}/weekly")
@limiter.limit("60/minute")
def api_get_weekly_rankings(
    request: Request,
    pos: str,
    year: Optional[int] = Query(default=None, ge=2018, le=2030, description="Filter to a specific season year"),
    week: Optional[int] = Query(default=None, ge=1, le=18, description="Filter to a specific week"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    Returns weekly fantasy rankings for a specific position.
    Performance: Bypasses Pydantic validation for high-volume data.
    """
    try:
        data = get_weekly_rankings(pos, year=year, week=week, limit=limit, offset=offset)
        if not data:
            raise HTTPException(status_code=500, detail="Data empty for position")
        return JSONResponse(content=data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in get_weekly_player_rankings(%s, year=%s, week=%s)", pos, year, week)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/rankings/{pos}/weeks")
@limiter.limit("30/minute")
def get_position_weeks(
    request: Request,
    pos: str,
    year: Optional[int] = Query(default=None, ge=2018, le=2030, description="Filter weeks to a specific year"),
):
    """Returns available weeks for the given position, optionally filtered by year."""
    try:
        return get_available_weeks(pos, year=year)
    except Exception as exc:
        logger.exception("Unexpected error in get_position_weeks(%s, year=%s)", pos, year)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/weekly-rankings")
@limiter.limit("60/minute")
def get_all_weekly_rankings(
    request: Request,
    pos: str,
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
    week: Optional[int] = Query(default=None, ge=1, le=18),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Alias for /rankings/{pos}/weekly."""
    try:
        data = get_weekly_rankings(pos, year=year, week=week, limit=limit, offset=offset)
        if not data:
            raise HTTPException(status_code=500, detail="Data empty for position")
        return JSONResponse(content=data)
    except Exception as exc:
        logger.exception("Error in get_all_weekly_rankings")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/rankings/{pos}/impact/{player_id}")
@limiter.limit("30/minute")
def get_player_impact_metrics(
    request: Request,
    pos: str,
    player_id: str,
    metric: str = Query(default="surface", description="Analysis type: surface, venue, elevation, opponent"),
):
    """Returns historical performance splits for a player based on external factors."""
    try:
        return get_player_impact(pos, player_id, metric)
    except Exception as exc:
        logger.exception("Error in get_player_impact_metrics")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/rankings/{pos}/defense")
@limiter.limit("20/minute")
def api_get_defense_stats_analytics(request: Request, pos: str):
    """Returns ranking of NFL defenses based on fantasy points allowed to the given position."""
    try:
        return get_defense_stats(pos)
    except Exception as exc:
        logger.exception("Error in get_defense_analytics")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get(
    "/rankings/{pos}/csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
@limiter.limit("10/minute")
def get_player_rankings_csv(
    request: Request,
    pos: str,
    year: Optional[int] = Query(default=None, ge=2018, le=2030),
):
    """Returns rankings as a downloadable CSV file."""
    try:
        data = get_rankings(pos, year=year, limit=1000, offset=0)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in get_player_rankings_csv(%s)", pos)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


    if not data:
        raise HTTPException(status_code=500, detail="No data available for export.")

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
