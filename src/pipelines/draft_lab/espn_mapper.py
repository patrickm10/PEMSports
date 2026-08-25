"""ESPN Fantasy JSON → Draft Lab DTOs (anti-corruption layer)."""

from __future__ import annotations

import json
from typing import Any, Optional

from pipelines.draft_lab.ids import draft_id_for, league_id_for, manager_id_for, pick_id_for
from pipelines.draft_lab.models import (
    MappedDraft,
    MappedEspnBundle,
    MappedLeague,
    MappedManager,
    MappedMarketRow,
    MappedPick,
)

# ESPN defaultPositionId → PEM Sports position codes.
ESPN_POSITION_ID = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE",
    5: "K",
    16: "DST",
}

# ESPN proTeamId → canonical abbreviation (TEAM_MAP keys).
ESPN_PRO_TEAM_ID = {
    0: "FA",
    1: "ATL",
    2: "BUF",
    3: "CHI",
    4: "CIN",
    5: "CLE",
    6: "DAL",
    7: "DEN",
    8: "DET",
    9: "GB",
    10: "TEN",
    11: "IND",
    12: "KC",
    13: "LV",
    14: "LAR",
    15: "MIA",
    16: "MIN",
    17: "NE",
    18: "NO",
    19: "NYG",
    20: "NYJ",
    21: "PHI",
    22: "ARI",
    23: "PIT",
    24: "LAC",
    25: "SF",
    26: "SEA",
    27: "TB",
    28: "WAS",
    29: "CAR",
    30: "JAX",
    33: "BAL",
    34: "HOU",
}

# ESPN lineupSlotId → roster slot label used in roster_slots_json.
ESPN_LINEUP_SLOT = {
    0: "QB",
    2: "RB",
    3: "RB_WR",
    4: "WR",
    6: "TE",
    16: "DST",
    17: "K",
    20: "BENCH",
    21: "IR",
    23: "FLEX",
    24: "SFLEX",
}

# ESPN statId 53 = receptions; points per reception decide scoring format.
_RECEPTION_STAT_ID = 53


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def scoring_from_settings(settings: dict[str, Any]) -> str:
    items = _as_list(_as_dict(settings.get("scoringSettings")).get("scoringItems"))
    rec_points: Optional[float] = None
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("statId") == _RECEPTION_STAT_ID:
            try:
                rec_points = float(item.get("points") or 0)
            except (TypeError, ValueError):
                rec_points = 0.0
            break
    if rec_points is not None:
        if rec_points >= 0.9:
            return "ppr"
        if rec_points >= 0.4:
            return "half"
        return "std"

    raw = str(settings.get("scoringType") or "").strip().lower()
    if raw in {"ppr", "half", "std"}:
        return raw
    if "half" in raw:
        return "half"
    if "ppr" in raw:
        return "ppr"
    name = str(settings.get("name") or "").lower()
    if "half" in name and "ppr" in name:
        return "half"
    if "ppr" in name:
        return "ppr"
    return "std"


def _roster_slots_json(settings: dict[str, Any]) -> str:
    counts = _as_dict(_as_dict(settings.get("rosterSettings")).get("lineupSlotCounts"))
    slots: dict[str, int] = {}
    for raw_id, raw_count in counts.items():
        try:
            slot_id = int(raw_id)
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        label = ESPN_LINEUP_SLOT.get(slot_id, f"SLOT_{slot_id}")
        slots[label] = slots.get(label, 0) + count
    return json.dumps(slots, sort_keys=True)


def _position_from_player(player: dict[str, Any]) -> str:
    pos_id = player.get("defaultPositionId")
    try:
        return ESPN_POSITION_ID.get(int(pos_id), "WR")
    except (TypeError, ValueError):
        return "WR"


def _team_from_player(player: dict[str, Any]) -> str:
    abbr = str(player.get("proTeamAbbreviation") or player.get("proTeamAbbr") or "").strip().upper()
    if abbr:
        return abbr
    try:
        return ESPN_PRO_TEAM_ID.get(int(player.get("proTeamId") or 0), "FA")
    except (TypeError, ValueError):
        return "FA"


def _player_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _as_list(payload.get("players")):
        if not isinstance(row, dict):
            continue
        inner = row.get("player") if isinstance(row.get("player"), dict) else row
        pid = inner.get("id", row.get("id"))
        if pid is None:
            continue
        out[str(pid)] = inner
    return out


def _market_rank_from_player(player: dict[str, Any]) -> Optional[int]:
    ranks = player.get("draftRanksById")
    if isinstance(ranks, dict):
        # Prefer rank set 0 (standard ESPN rank), else first numeric rank.
        preferred = ranks.get("0") or ranks.get(0)
        candidates = [preferred] if isinstance(preferred, dict) else []
        if not candidates:
            candidates = [v for v in ranks.values() if isinstance(v, dict)]
        for block in candidates:
            rank = block.get("rank")
            try:
                value = int(rank)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    for key in ("draftRank", "rank"):
        try:
            value = int(player.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _owner_id_for_team(team: dict[str, Any], espn_league_id: str) -> str:
    owners = _as_list(team.get("owners"))
    if owners:
        return str(owners[0])
    team_id = team.get("id")
    if team_id is None:
        return f"team-unknown-{espn_league_id}"
    return f"team-{team_id}"


def _display_name(
    team: dict[str, Any],
    owner_id: str,
    members_by_id: dict[str, dict[str, Any]],
) -> str:
    member = members_by_id.get(owner_id) or {}
    name = str(member.get("displayName") or member.get("firstName") or "").strip()
    if name:
        return name
    loc = str(team.get("location") or "").strip()
    nick = str(team.get("nickname") or "").strip()
    combined = f"{loc} {nick}".strip()
    if combined:
        return combined
    return str(team.get("abbrev") or owner_id)


def map_espn_payload(
    payload: dict[str, Any],
    *,
    source: str,
    as_of: str = "fixture",
    provider: str = "fixture",
) -> MappedEspnBundle:
    """Map one ESPN league+draft JSON object into canonical Draft Lab DTOs."""
    if not isinstance(payload, dict):
        raise ValueError("ESPN payload must be an object")

    settings = _as_dict(payload.get("settings"))
    espn_league_id = str(payload.get("id") or payload.get("leagueId") or "")
    if not espn_league_id:
        raise ValueError("ESPN payload missing league id")

    try:
        season = int(payload.get("seasonId") or settings.get("seasonId") or 0)
    except (TypeError, ValueError):
        season = 0
    if season <= 0:
        raise ValueError("ESPN payload missing seasonId")

    draft_settings = _as_dict(settings.get("draftSettings"))
    draft_type = str(draft_settings.get("type") or "SNAKE").strip().upper()
    if draft_type != "SNAKE":
        # v1 stores snake only; auction/other payloads are rejected at the mapper.
        raise ValueError(f"Unsupported ESPN draft type {draft_type!r} (snake only)")

    teams = [t for t in _as_list(payload.get("teams")) if isinstance(t, dict)]
    members_by_id = {
        str(m.get("id")): m
        for m in _as_list(payload.get("members"))
        if isinstance(m, dict) and m.get("id") is not None
    }
    team_count = int(settings.get("size") or len(teams) or 0)
    if team_count <= 0:
        raise ValueError("ESPN payload has no teams")

    league_id = league_id_for(espn_league_id)
    draft_id = draft_id_for(espn_league_id, season)
    scoring = scoring_from_settings(settings)

    managers: list[MappedManager] = []
    team_id_to_manager: dict[int, str] = {}
    for team in teams:
        try:
            espn_team_id = int(team.get("id"))
        except (TypeError, ValueError):
            continue
        owner_id = _owner_id_for_team(team, espn_league_id)
        mid = manager_id_for(espn_league_id, owner_id)
        team_id_to_manager[espn_team_id] = mid
        managers.append(
            MappedManager(
                manager_id=mid,
                league_id=league_id,
                espn_owner_id=owner_id,
                display_name=_display_name(team, owner_id, members_by_id),
                team_abbrev=str(team.get("abbrev") or "").strip() or f"T{espn_team_id}",
                espn_team_id=espn_team_id,
            )
        )

    pick_order_team_ids = _as_list(draft_settings.get("pickOrder"))
    if not pick_order_team_ids:
        pick_order_team_ids = [m.espn_team_id for m in sorted(managers, key=lambda x: x.espn_team_id)]
    pick_order_manager_ids: list[str] = []
    for raw_tid in pick_order_team_ids:
        try:
            tid = int(raw_tid)
        except (TypeError, ValueError):
            continue
        mid = team_id_to_manager.get(tid)
        if mid:
            pick_order_manager_ids.append(mid)

    players = _player_index(payload)
    raw_picks = _as_list(_as_dict(payload.get("draftDetail")).get("picks"))
    try:
        rounds = int(draft_settings.get("rounds") or 0)
    except (TypeError, ValueError):
        rounds = 0
    if rounds <= 0 and raw_picks:
        try:
            rounds = max(int(p.get("roundId") or 0) for p in raw_picks if isinstance(p, dict))
        except ValueError:
            rounds = 0

    picks: list[MappedPick] = []
    for raw in raw_picks:
        if not isinstance(raw, dict):
            continue
        try:
            overall = int(raw.get("overallPickNumber") or 0)
            round_id = int(raw.get("roundId") or 0)
            round_pick = int(raw.get("roundPickNumber") or 0)
            team_id = int(raw.get("teamId") or 0)
            espn_pid = raw.get("playerId")
        except (TypeError, ValueError):
            continue
        if overall <= 0 or espn_pid is None:
            continue
        manager_id = team_id_to_manager.get(team_id)
        if not manager_id:
            continue
        player = players.get(str(espn_pid), {})
        picks.append(
            MappedPick(
                pick_id=pick_id_for(draft_id, overall),
                draft_id=draft_id,
                league_id=league_id,
                season=season,
                overall_pick=overall,
                round=round_id,
                round_pick=round_pick,
                manager_id=manager_id,
                espn_player_id=str(espn_pid),
                player_name=str(player.get("fullName") or raw.get("playerName") or "").strip(),
                position=_position_from_player(player) if player else "WR",
                team=_team_from_player(player) if player else "FA",
            )
        )
    picks.sort(key=lambda p: p.overall_pick)
    if rounds <= 0:
        rounds = max((p.round for p in picks), default=0)

    market: list[MappedMarketRow] = []
    seen_market: set[str] = set()
    for espn_pid, player in players.items():
        rank = _market_rank_from_player(player)
        if rank is None:
            continue
        if espn_pid in seen_market:
            continue
        seen_market.add(espn_pid)
        market.append(
            MappedMarketRow(
                provider=provider,
                season=season,
                scoring=scoring,
                as_of=as_of,
                espn_player_id=espn_pid,
                player_name=str(player.get("fullName") or "").strip(),
                position=_position_from_player(player),
                team=_team_from_player(player),
                market_rank=rank,
                adp=float(rank),
                auction_value=None,
            )
        )
    market.sort(key=lambda r: (r.market_rank, r.espn_player_id))

    league = MappedLeague(
        league_id=league_id,
        espn_league_id=espn_league_id,
        name=str(settings.get("name") or payload.get("name") or f"League {espn_league_id}"),
        scoring=scoring,
        team_count=team_count,
        roster_slots_json=_roster_slots_json(settings),
        source=source,
        season=season,
    )
    draft = MappedDraft(
        draft_id=draft_id,
        league_id=league_id,
        season=season,
        draft_type="SNAKE",
        rounds=rounds,
        pick_count=len(picks),
        pick_order_json=json.dumps(pick_order_manager_ids),
    )
    return MappedEspnBundle(
        league=league,
        draft=draft,
        managers=managers,
        picks=picks,
        market=market,
    )


def map_espn_payloads(payloads: list[Any], **kwargs: Any) -> list[MappedEspnBundle]:
    bundles: list[MappedEspnBundle] = []
    for raw in payloads:
        if isinstance(raw, list):
            bundles.extend(map_espn_payloads(raw, **kwargs))
        elif isinstance(raw, dict):
            bundles.append(map_espn_payload(raw, **kwargs))
    return bundles
