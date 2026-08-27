"""Deterministic snake-draft recommendation engine."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Optional

VALID_MODELS = ("market_only", "market_plus_manager")


@dataclass
class SimPlayer:
    espn_player_id: str
    player_name: str
    position: str
    team: str
    market_rank: int
    player_id: Optional[str] = None


@dataclass
class SimRecommendation:
    player_id: Optional[str]
    espn_player_id: str
    player_name: str
    position: str
    team: str
    market_rank: int
    market_component: float
    roster_need_component: float
    manager_position_component: float
    combined_score: float
    explanation: dict

    def as_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "espn_player_id": self.espn_player_id,
            "player_name": self.player_name,
            "position": self.position,
            "team": self.team,
            "market_rank": self.market_rank,
            "market_component": self.market_component,
            "roster_need_component": self.roster_need_component,
            "manager_position_component": self.manager_position_component,
            "combined_score": self.combined_score,
            "explanation": self.explanation,
        }


@dataclass
class SimulateResult:
    model: str
    seed: int
    overall_pick: int
    recommendations: list[SimRecommendation] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "seed": self.seed,
            "overall_pick": self.overall_pick,
            "recommendations": [r.as_dict() for r in self.recommendations],
        }


def parse_roster_slots(roster_slots_json: str) -> dict[str, int]:
    try:
        raw = json.loads(roster_slots_json or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        try:
            out[str(key).upper()] = int(value)
        except (TypeError, ValueError):
            continue
    return out


def parse_share_json(raw: str) -> dict[str, float]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in data.items():
        try:
            out[str(key).upper()] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def market_component(rank: int) -> float:
    if rank <= 0:
        return 0.0
    return round(1.0 / float(rank), 6)


def roster_need_component(
    position: str,
    *,
    roster_counts: dict[str, int],
    roster_slots: dict[str, int],
) -> float:
    pos = (position or "").upper()
    filled = roster_counts.get(pos, 0)
    slots = roster_slots.get(pos, 0)
    if slots > 0 and filled < slots:
        return 1.0
    if pos in {"RB", "WR", "TE"}:
        flex_slots = roster_slots.get("FLEX", 0)
        flex_used = 0
        for flex_pos in ("RB", "WR", "TE"):
            flex_used += max(
                0, roster_counts.get(flex_pos, 0) - roster_slots.get(flex_pos, 0)
            )
        if flex_slots > 0 and flex_used < flex_slots:
            return 0.6
    if roster_slots.get("BENCH", 0) > 0:
        return 0.25
    return 0.0


def manager_position_component(
    position: str,
    *,
    overall_pick: int,
    team_count: int,
    early_share: dict[str, float],
    position_share: dict[str, float],
    sample_size_ok: bool,
) -> float:
    if not sample_size_ok:
        return 0.0
    pos = (position or "").upper()
    round_num = ((overall_pick - 1) // max(team_count, 1)) + 1
    source = early_share if round_num <= 3 else position_share
    return round(float(source.get(pos, 0.0)), 6)


def recommend(
    *,
    remaining: list[SimPlayer],
    roster_counts: dict[str, int],
    roster_slots: dict[str, int],
    overall_pick: int,
    team_count: int,
    model: str,
    seed: int = 0,
    limit: int = 5,
    early_share: Optional[dict[str, float]] = None,
    position_share: Optional[dict[str, float]] = None,
    sample_size_ok: bool = False,
) -> SimulateResult:
    if model not in VALID_MODELS:
        raise ValueError(f"Invalid model {model!r}")
    if overall_pick < 1:
        raise ValueError("overall_pick must be >= 1")
    rng = random.Random(seed)
    _ = rng.random()  # consume seed so identical seeds stay aligned if jitter is added later

    early = early_share or {}
    shares = position_share or {}
    scored: list[SimRecommendation] = []
    for player in remaining:
        m_comp = market_component(player.market_rank)
        r_comp = roster_need_component(
            player.position, roster_counts=roster_counts, roster_slots=roster_slots
        )
        g_comp = manager_position_component(
            player.position,
            overall_pick=overall_pick,
            team_count=team_count,
            early_share=early,
            position_share=shares,
            sample_size_ok=sample_size_ok,
        )
        if model == "market_only":
            combined = m_comp
            used_roster = 0.0
            used_manager = 0.0
        else:
            combined = round(m_comp + r_comp + g_comp, 6)
            used_roster = r_comp
            used_manager = g_comp
        explanation = {
            "summary": (
                f"Market rank {player.market_rank}; "
                f"roster need {used_roster}; "
                f"manager position prior {used_manager}"
            ),
            "components": {
                "market_component": m_comp,
                "roster_need_component": used_roster,
                "manager_position_component": used_manager,
            },
            "model": model,
        }
        scored.append(
            SimRecommendation(
                player_id=player.player_id,
                espn_player_id=player.espn_player_id,
                player_name=player.player_name,
                position=player.position,
                team=player.team,
                market_rank=player.market_rank,
                market_component=m_comp,
                roster_need_component=used_roster,
                manager_position_component=used_manager,
                combined_score=combined,
                explanation=explanation,
            )
        )

    if model == "market_only":
        scored.sort(key=lambda r: (r.market_rank, r.player_id or "", r.espn_player_id))
    else:
        scored.sort(
            key=lambda r: (-r.combined_score, r.player_id or "", r.espn_player_id)
        )
    return SimulateResult(
        model=model,
        seed=seed,
        overall_pick=overall_pick,
        recommendations=scored[: max(1, limit)],
    )


def snake_on_the_clock(
    overall_pick: int,
    pick_order_manager_ids: list[str],
    team_count: int,
) -> Optional[str]:
    if overall_pick < 1 or not pick_order_manager_ids:
        return None
    n = team_count if team_count > 0 else len(pick_order_manager_ids)
    if n <= 0:
        return None
    round_index = (overall_pick - 1) // n
    slot = (overall_pick - 1) % n
    if round_index % 2 == 1:
        slot = n - 1 - slot
    if slot >= len(pick_order_manager_ids):
        return None
    return pick_order_manager_ids[slot]


def roster_counts_from_picks(picks: list, *, manager_id: str, before_overall: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pick in picks:
        if getattr(pick, "manager_id", None) != manager_id:
            continue
        overall = getattr(pick, "overall_pick", None)
        if overall is None:
            continue
        if int(overall) >= before_overall:
            continue
        pos = str(getattr(pick, "position", "") or "").upper()
        if not pos:
            continue
        counts[pos] = counts.get(pos, 0) + 1
    return counts
