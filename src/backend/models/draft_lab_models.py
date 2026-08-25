"""Stable Draft Lab API contracts. All keys present; missing values are null."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeagueRecord(_Frozen):
    league_id: str
    espn_league_id: str
    name: str
    scoring: str
    team_count: int
    roster_slots: dict[str, int]
    source: str


class LeagueList(_Frozen):
    leagues: list[LeagueRecord]


class DraftRecord(_Frozen):
    draft_id: str
    league_id: str
    season: int
    draft_type: str
    rounds: int
    pick_count: int
    pick_order: list[str]


class DraftList(_Frozen):
    drafts: list[DraftRecord]


class PickRecord(_Frozen):
    pick_id: str
    draft_id: str
    league_id: str
    season: int
    overall_pick: int
    round: int
    round_pick: int
    manager_id: str
    player_id: Optional[str] = None
    espn_player_id: str
    player_name: str
    position: str
    team: str
    resolution_status: str
    resolution_reason: Optional[str] = None


class PickList(_Frozen):
    draft_id: str
    picks: list[PickRecord]


class ManagerProfileRecord(_Frozen):
    season_from: Optional[int] = None
    season_to: Optional[int] = None
    n_picks: Optional[int] = None
    n_drafts: Optional[int] = None
    mean_reach: Optional[float] = None
    median_reach: Optional[float] = None
    early_position_share: dict[str, float]
    position_share: dict[str, float]
    sample_size_ok: bool


class ManagerRecord(_Frozen):
    manager_id: str
    league_id: str
    espn_owner_id: str
    display_name: str
    team_abbrev: str
    profile: Optional[ManagerProfileRecord] = None


class MarketRow(_Frozen):
    provider: str
    season: int
    scoring: str
    as_of: str
    player_id: Optional[str] = None
    espn_player_id: str
    player_name: str
    position: str
    team: str
    market_rank: int
    adp: Optional[float] = None
    auction_value: Optional[float] = None


class MarketList(_Frozen):
    market: list[MarketRow]


class BacktestRecord(_Frozen):
    backtest_id: str
    draft_id: str
    model: str
    exact_hit_rate: Optional[float] = None
    top3_hit_rate: Optional[float] = None
    mean_abs_rank_error: Optional[float] = None
    position_hit_rate: Optional[float] = None
    n_picks: Optional[int] = None
    n_skipped: Optional[int] = None
    seed: Optional[int] = None


class BacktestList(_Frozen):
    backtests: list[BacktestRecord]


class SimulateRequest(_Frozen):
    draft_id: str
    overall_pick: int = Field(ge=1)
    model: Literal["market_only", "market_plus_manager"]
    seed: int = 0
    limit: int = Field(default=5, ge=1, le=25)


class RecommendationRecord(_Frozen):
    player_id: Optional[str] = None
    espn_player_id: str
    player_name: str
    position: str
    team: str
    market_rank: int
    market_component: float
    roster_need_component: float
    manager_position_component: float
    combined_score: float
    explanation: dict[str, Any]


class SimulateResponse(_Frozen):
    draft_id: str
    overall_pick: int
    model: str
    seed: int
    on_the_clock_manager_id: Optional[str] = None
    recommendations: list[RecommendationRecord]
