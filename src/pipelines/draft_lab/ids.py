"""Canonical Draft Lab identifiers (UUID5). ESPN ids are never canonical."""

from __future__ import annotations

import uuid

# Separate from scripts/build_players_dimension.py PLAYER_ID_NAMESPACE.
DRAFT_LAB_ID_NAMESPACE = uuid.UUID("c8e4a1b2-7d3f-4e91-9c05-6a8b2d4f1e03")


def league_id_for(espn_league_id: str | int) -> str:
    return str(uuid.uuid5(DRAFT_LAB_ID_NAMESPACE, f"espn:{espn_league_id}"))


def draft_id_for(espn_league_id: str | int, season: int) -> str:
    return str(uuid.uuid5(DRAFT_LAB_ID_NAMESPACE, f"espn:{espn_league_id}:{season}"))


def manager_id_for(espn_league_id: str | int, espn_owner_id: str) -> str:
    return str(
        uuid.uuid5(DRAFT_LAB_ID_NAMESPACE, f"espn:{espn_league_id}:{espn_owner_id}")
    )


def pick_id_for(draft_id: str, overall_pick: int) -> str:
    return str(uuid.uuid5(DRAFT_LAB_ID_NAMESPACE, f"{draft_id}:{overall_pick}"))


def backtest_id_for(draft_id: str, model: str, seed: int) -> str:
    return str(uuid.uuid5(DRAFT_LAB_ID_NAMESPACE, f"backtest:{draft_id}:{model}:{seed}"))
