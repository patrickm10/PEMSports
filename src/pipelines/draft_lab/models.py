"""Internal Draft Lab DTOs. ESPN payloads never leak past espn_mapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MappedLeague:
    league_id: str
    espn_league_id: str
    name: str
    scoring: str
    team_count: int
    roster_slots_json: str
    source: str
    season: int


@dataclass
class MappedDraft:
    draft_id: str
    league_id: str
    season: int
    draft_type: str
    rounds: int
    pick_count: int
    pick_order_json: str


@dataclass
class MappedManager:
    manager_id: str
    league_id: str
    espn_owner_id: str
    display_name: str
    team_abbrev: str
    espn_team_id: int


@dataclass
class MappedPick:
    pick_id: str
    draft_id: str
    league_id: str
    season: int
    overall_pick: int
    round: int
    round_pick: int
    manager_id: str
    espn_player_id: str
    player_name: str
    position: str
    team: str
    player_id: Optional[str] = None
    resolution_status: str = "unresolved"
    resolution_reason: Optional[str] = None


@dataclass
class MappedMarketRow:
    provider: str
    season: int
    scoring: str
    as_of: str
    espn_player_id: str
    player_name: str
    position: str
    team: str
    market_rank: int
    adp: Optional[float] = None
    auction_value: Optional[float] = None
    player_id: Optional[str] = None


@dataclass
class MappedEspnBundle:
    league: MappedLeague
    draft: MappedDraft
    managers: list[MappedManager]
    picks: list[MappedPick]
    market: list[MappedMarketRow]
    extras: dict[str, Any] = field(default_factory=dict)
