"""Smallest useful manager profile: reach vs market and position shares."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import Optional

from pipelines.draft_lab.models import MappedMarketRow, MappedPick

EARLY_ROUND_MAX = 3
MIN_PICKS_FOR_SAMPLE = 3


@dataclass
class ManagerProfile:
    manager_id: str
    league_id: str
    season_from: int
    season_to: int
    n_picks: int
    n_drafts: int
    mean_reach: Optional[float]
    median_reach: Optional[float]
    early_position_share_json: str
    position_share_json: str
    sample_size_ok: bool


def _shares(positions: list[str]) -> dict[str, float]:
    if not positions:
        return {}
    counts: dict[str, int] = {}
    for pos in positions:
        key = (pos or "").upper() or "UNK"
        counts[key] = counts.get(key, 0) + 1
    total = float(len(positions))
    return {k: round(v / total, 4) for k, v in sorted(counts.items())}


def build_manager_profiles(
    picks: list[MappedPick],
    market: list[MappedMarketRow],
) -> list[ManagerProfile]:
    rank_by_espn: dict[tuple[int, str], int] = {}
    for row in market:
        rank_by_espn[(row.season, row.espn_player_id)] = row.market_rank

    grouped: dict[tuple[str, str], list[MappedPick]] = {}
    for pick in picks:
        grouped.setdefault((pick.manager_id, pick.league_id), []).append(pick)

    profiles: list[ManagerProfile] = []
    for (manager_id, league_id), group in grouped.items():
        group.sort(key=lambda p: (p.season, p.overall_pick))
        seasons = [p.season for p in group]
        drafts = {p.draft_id for p in group}
        reaches: list[float] = []
        all_pos: list[str] = []
        early_pos: list[str] = []
        for pick in group:
            all_pos.append(pick.position)
            if pick.round <= EARLY_ROUND_MAX:
                early_pos.append(pick.position)
            rank = rank_by_espn.get((pick.season, pick.espn_player_id))
            if rank is None:
                continue
            reaches.append(float(pick.overall_pick - rank))
        n_picks = len(group)
        profiles.append(
            ManagerProfile(
                manager_id=manager_id,
                league_id=league_id,
                season_from=min(seasons) if seasons else 0,
                season_to=max(seasons) if seasons else 0,
                n_picks=n_picks,
                n_drafts=len(drafts),
                mean_reach=round(statistics.fmean(reaches), 4) if reaches else None,
                median_reach=round(float(statistics.median(reaches)), 4) if reaches else None,
                early_position_share_json=json.dumps(_shares(early_pos), sort_keys=True),
                position_share_json=json.dumps(_shares(all_pos), sort_keys=True),
                sample_size_ok=n_picks >= MIN_PICKS_FOR_SAMPLE,
            )
        )
    profiles.sort(key=lambda p: (p.league_id, p.manager_id))
    return profiles
