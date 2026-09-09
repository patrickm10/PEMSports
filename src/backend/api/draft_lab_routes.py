"""API v1 routes — Draft Lab bounded context.

Contract:
- Schema-stable JSON: documented keys always present; missing values are null.
- Explicit resources; no polymorphic query params for core dimensions.
- Backend owns aggregation and simulation. No request-time DuckDB writes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from backend.core.authz import require_draft_lab
from backend.core.limiter import limiter
from backend.models.draft_lab_models import (
    BacktestList,
    DraftList,
    DraftRecord,
    LeagueList,
    LeagueRecord,
    ManagerRecord,
    MarketList,
    PickList,
    SimulateRequest,
    SimulateResponse,
)
from backend.services import draft_lab_service

router = APIRouter(prefix="/draft-lab", dependencies=[Depends(require_draft_lab)])


@router.get("/leagues", response_model=LeagueList)
@limiter.limit("60/minute")
def api_list_leagues(request: Request) -> LeagueList:
    return draft_lab_service.list_leagues()


@router.get("/leagues/{league_id}", response_model=LeagueRecord)
@limiter.limit("60/minute")
def api_get_league(request: Request, league_id: str) -> LeagueRecord:
    return draft_lab_service.get_league(league_id)


@router.get("/drafts", response_model=DraftList)
@limiter.limit("60/minute")
def api_list_drafts(
    request: Request,
    league_id: Optional[str] = Query(default=None),
    season: Optional[int] = Query(default=None, ge=2018, le=2030),
) -> DraftList:
    return draft_lab_service.list_drafts(league_id=league_id, season=season)


@router.get("/drafts/{draft_id}", response_model=DraftRecord)
@limiter.limit("60/minute")
def api_get_draft(request: Request, draft_id: str) -> DraftRecord:
    return draft_lab_service.get_draft(draft_id)


@router.get("/drafts/{draft_id}/picks", response_model=PickList)
@limiter.limit("60/minute")
def api_list_picks(request: Request, draft_id: str) -> PickList:
    return draft_lab_service.list_picks(draft_id)


@router.get("/managers/{manager_id}", response_model=ManagerRecord)
@limiter.limit("60/minute")
def api_get_manager(request: Request, manager_id: str) -> ManagerRecord:
    return draft_lab_service.get_manager(manager_id)


@router.get("/market", response_model=MarketList)
@limiter.limit("60/minute")
def api_list_market(
    request: Request,
    season: Optional[int] = Query(default=None, ge=2018, le=2030),
    scoring: Optional[str] = Query(default=None, pattern="^(ppr|half|std)$"),
    provider: Optional[str] = Query(default=None),
) -> MarketList:
    return draft_lab_service.list_market(season=season, scoring=scoring, provider=provider)


@router.post("/simulate", response_model=SimulateResponse)
@limiter.limit("20/minute")
def api_simulate(request: Request, body: SimulateRequest) -> SimulateResponse:
    return draft_lab_service.simulate(body)


@router.get("/backtests", response_model=BacktestList)
@limiter.limit("30/minute")
def api_list_backtests(
    request: Request,
    draft_id: Optional[str] = Query(default=None),
) -> BacktestList:
    return draft_lab_service.list_backtests(draft_id=draft_id)
