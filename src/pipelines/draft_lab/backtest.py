"""Replay historical snake drafts: market_only vs market_plus_manager."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pipelines.draft_lab.ids import backtest_id_for
from pipelines.draft_lab.manager_profiles import ManagerProfile
from pipelines.draft_lab.models import MappedDraft, MappedMarketRow, MappedPick
from pipelines.draft_lab.simulate import (
    SimPlayer,
    parse_roster_slots,
    parse_share_json,
    recommend,
    roster_counts_from_picks,
    snake_on_the_clock,
)

BACKTEST_MODELS = ("market_only", "market_plus_manager")


@dataclass
class BacktestResult:
    backtest_id: str
    draft_id: str
    model: str
    exact_hit_rate: Optional[float]
    top3_hit_rate: Optional[float]
    mean_abs_rank_error: Optional[float]
    position_hit_rate: Optional[float]
    n_picks: int
    n_skipped: int
    seed: int


def _profile_for(manager_id: str, profiles: list[ManagerProfile]) -> Optional[ManagerProfile]:
    for profile in profiles:
        if profile.manager_id == manager_id:
            return profile
    return None


def run_backtest(
    *,
    draft: MappedDraft,
    picks: list[MappedPick],
    market: list[MappedMarketRow],
    profiles: list[ManagerProfile],
    roster_slots_json: str,
    model: str,
    seed: int = 0,
    pick_order_manager_ids: Optional[list[str]] = None,
) -> BacktestResult:
    if model not in BACKTEST_MODELS:
        raise ValueError(f"Invalid model {model!r}")

    roster_slots = parse_roster_slots(roster_slots_json)
    order = pick_order_manager_ids or []
    if not order:
        try:
            parsed = json.loads(draft.pick_order_json or "[]")
            if isinstance(parsed, list):
                order = [str(x) for x in parsed]
        except json.JSONDecodeError:
            order = []

    drafted: list[MappedPick] = []
    exact = 0
    top3 = 0
    pos_hits = 0
    abs_err: list[float] = []
    evaluated = 0
    skipped = 0

    market_by_espn = {row.espn_player_id: row for row in market}

    for actual in sorted(picks, key=lambda p: p.overall_pick):
        remaining: list[SimPlayer] = []
        taken = {p.espn_player_id for p in drafted}
        for row in market:
            if row.espn_player_id in taken:
                continue
            remaining.append(
                SimPlayer(
                    espn_player_id=row.espn_player_id,
                    player_name=row.player_name,
                    position=row.position,
                    team=row.team,
                    market_rank=row.market_rank,
                    player_id=row.player_id,
                )
            )
        if not remaining:
            skipped += 1
            drafted.append(actual)
            continue

        n_teams = len(order) if order else max(len({p.manager_id for p in picks}), 1)
        manager_id = snake_on_the_clock(actual.overall_pick, order, n_teams) or actual.manager_id

        profile = _profile_for(manager_id, profiles)
        counts = roster_counts_from_picks(
            drafted, manager_id=manager_id, before_overall=actual.overall_pick
        )
        result = recommend(
            remaining=remaining,
            roster_counts=counts,
            roster_slots=roster_slots,
            overall_pick=actual.overall_pick,
            team_count=n_teams,
            model=model,
            seed=seed,
            limit=3,
            early_share=parse_share_json(profile.early_position_share_json) if profile else {},
            position_share=parse_share_json(profile.position_share_json) if profile else {},
            sample_size_ok=bool(profile and profile.sample_size_ok),
        )
        recs = result.recommendations
        if not recs:
            skipped += 1
            drafted.append(actual)
            continue

        actual_key = actual.player_id or actual.espn_player_id
        if actual.resolution_status != "resolved" and not actual.player_id:
            # Still evaluate on espn id so unresolved actuals are not dropped from storage;
            # they are excluded from identity-sensitive exact-match when player_id is missing
            # but espn id comparison still applies.
            pass

        top_ids = [(r.player_id or r.espn_player_id) for r in recs]
        predicted = recs[0]
        pred_key = predicted.player_id or predicted.espn_player_id
        evaluated += 1
        if pred_key == actual_key:
            exact += 1
        if actual_key in top_ids:
            top3 += 1
        if predicted.position == actual.position:
            pos_hits += 1
        actual_rank = market_by_espn.get(actual.espn_player_id)
        if actual_rank is not None:
            abs_err.append(abs(predicted.market_rank - actual_rank.market_rank))
        drafted.append(actual)

    n = evaluated
    return BacktestResult(
        backtest_id=backtest_id_for(draft.draft_id, model, seed),
        draft_id=draft.draft_id,
        model=model,
        exact_hit_rate=round(exact / n, 4) if n else None,
        top3_hit_rate=round(top3 / n, 4) if n else None,
        mean_abs_rank_error=round(sum(abs_err) / len(abs_err), 4) if abs_err else None,
        position_hit_rate=round(pos_hits / n, 4) if n else None,
        n_picks=n,
        n_skipped=skipped,
        seed=seed,
    )


def run_backtests_for_draft(**kwargs) -> list[BacktestResult]:
    seed = int(kwargs.get("seed") or 0)
    results = []
    for model in BACKTEST_MODELS:
        payload = dict(kwargs)
        payload["model"] = model
        payload["seed"] = seed
        results.append(run_backtest(**payload))
    return results
