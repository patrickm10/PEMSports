"""Draft Lab service — orchestrates query + deterministic simulation."""

from __future__ import annotations

from typing import Optional

from backend.core.exceptions import InvalidRequestError
from backend.data import draft_lab_query
from backend.models.draft_lab_models import (
    BacktestList,
    BacktestRecord,
    DraftList,
    DraftRecord,
    LeagueList,
    LeagueRecord,
    ManagerProfileRecord,
    ManagerRecord,
    MarketList,
    MarketRow,
    PickList,
    PickRecord,
    RecommendationRecord,
    SimulateRequest,
    SimulateResponse,
)
from pipelines.draft_lab.simulate import (
    SimPlayer,
    recommend,
    roster_counts_from_picks,
    snake_on_the_clock,
)


def list_leagues() -> LeagueList:
    return LeagueList(leagues=[LeagueRecord.model_validate(r) for r in draft_lab_query.query_leagues()])


def get_league(league_id: str) -> LeagueRecord:
    return LeagueRecord.model_validate(draft_lab_query.query_league(league_id))


def list_drafts(*, league_id: Optional[str] = None, season: Optional[int] = None) -> DraftList:
    rows = draft_lab_query.query_drafts(league_id=league_id, season=season)
    return DraftList(drafts=[DraftRecord.model_validate(r) for r in rows])


def get_draft(draft_id: str) -> DraftRecord:
    return DraftRecord.model_validate(draft_lab_query.query_draft(draft_id))


def list_picks(draft_id: str) -> PickList:
    get_draft(draft_id)
    rows = draft_lab_query.query_picks(draft_id)
    return PickList(draft_id=draft_id, picks=[PickRecord.model_validate(r) for r in rows])


def get_manager(manager_id: str) -> ManagerRecord:
    row = draft_lab_query.query_manager(manager_id)
    profile = row.get("profile")
    return ManagerRecord(
        manager_id=row["manager_id"],
        league_id=row["league_id"],
        espn_owner_id=row["espn_owner_id"],
        display_name=row["display_name"],
        team_abbrev=row["team_abbrev"],
        profile=ManagerProfileRecord.model_validate(profile) if profile else None,
    )


def list_market(
    *,
    season: Optional[int] = None,
    scoring: Optional[str] = None,
    provider: Optional[str] = None,
) -> MarketList:
    rows = draft_lab_query.query_market(season=season, scoring=scoring, provider=provider)
    return MarketList(market=[MarketRow.model_validate(r) for r in rows])


def list_backtests(*, draft_id: Optional[str] = None) -> BacktestList:
    rows = draft_lab_query.query_backtests(draft_id=draft_id)
    return BacktestList(backtests=[BacktestRecord.model_validate(r) for r in rows])


class _PickView:
    def __init__(self, row: dict):
        self.manager_id = row["manager_id"]
        self.overall_pick = row["overall_pick"]
        self.position = row["position"]


def simulate(req: SimulateRequest) -> SimulateResponse:
    ctx = draft_lab_query.query_simulation_context(req.draft_id)
    draft = ctx["draft"]
    pick_count = int(draft["pick_count"] or 0)
    if pick_count > 0 and req.overall_pick > pick_count:
        raise InvalidRequestError(
            f"overall_pick {req.overall_pick} is outside draft range 1..{pick_count}"
        )

    team_count = int(ctx["league"]["team_count"] or 0)
    order = [str(x) for x in (draft.get("pick_order") or [])]
    manager_id = snake_on_the_clock(req.overall_pick, order, team_count)

    taken = {
        str(p["espn_player_id"])
        for p in ctx["picks"]
        if p.get("overall_pick") is not None and int(p["overall_pick"]) < req.overall_pick
    }
    remaining = [
        SimPlayer(
            espn_player_id=str(row["espn_player_id"]),
            player_name=row.get("player_name") or "",
            position=row.get("position") or "",
            team=row.get("team") or "",
            market_rank=int(row["market_rank"]),
            player_id=row.get("player_id"),
        )
        for row in ctx["market"]
        if row.get("espn_player_id") and str(row["espn_player_id"]) not in taken
        and row.get("market_rank") is not None
    ]

    roster_slots = {
        str(k).upper(): int(v) for k, v in (ctx["league"].get("roster_slots") or {}).items()
    }
    prior = [_PickView(p) for p in ctx["picks"]]
    counts = roster_counts_from_picks(
        prior, manager_id=manager_id or "", before_overall=req.overall_pick
    )

    profile = None
    if manager_id:
        for item in ctx["profiles"]:
            if item.get("manager_id") == manager_id:
                profile = item
                break

    result = recommend(
        remaining=remaining,
        roster_counts=counts,
        roster_slots=roster_slots,
        overall_pick=req.overall_pick,
        team_count=team_count or len(order) or 1,
        model=req.model,
        seed=req.seed,
        limit=req.limit,
        early_share=(profile or {}).get("early_position_share") or {},
        position_share=(profile or {}).get("position_share") or {},
        sample_size_ok=bool((profile or {}).get("sample_size_ok")),
    )
    return SimulateResponse(
        draft_id=req.draft_id,
        overall_pick=req.overall_pick,
        model=result.model,
        seed=result.seed,
        on_the_clock_manager_id=manager_id,
        recommendations=[RecommendationRecord.model_validate(r.as_dict()) for r in result.recommendations],
    )
