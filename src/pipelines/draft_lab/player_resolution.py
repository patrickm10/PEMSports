"""Resolve ESPN player ids to PEM Sports canonical player_id."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from pipelines.constants import TEAM_MAP
from pipelines.draft_lab.models import MappedMarketRow, MappedPick
from pipelines.draft_lab.names import normalize_name

RESOLUTION_RESOLVED = "resolved"
RESOLUTION_UNRESOLVED = "unresolved"
RESOLUTION_AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class PlayerDimRow:
    player_id: str
    player_name: str
    team: str
    position: str
    espn_player_id: str


@dataclass
class ResolutionReport:
    resolved: int = 0
    unresolved: int = 0
    ambiguous: int = 0

    def add(self, status: str) -> None:
        if status == RESOLUTION_RESOLVED:
            self.resolved += 1
        elif status == RESOLUTION_AMBIGUOUS:
            self.ambiguous += 1
        else:
            self.unresolved += 1


def load_players_dimension(players_csv: Path) -> list[PlayerDimRow]:
    if not players_csv.exists():
        return []
    rows: list[PlayerDimRow] = []
    with players_csv.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            pid = str(raw.get("player_id") or "").strip()
            if not pid:
                continue
            rows.append(
                PlayerDimRow(
                    player_id=pid,
                    player_name=str(raw.get("player_name") or "").strip(),
                    team=str(raw.get("team") or "").strip().upper(),
                    position=str(raw.get("position") or "").strip().upper(),
                    espn_player_id=str(raw.get("espn_player_id") or "").strip(),
                )
            )
    return rows


def _dst_aliases(team: str) -> set[str]:
    abbr = (team or "").strip().upper()
    slug = TEAM_MAP.get(abbr, "")
    names = {abbr.lower(), f"{abbr.lower()} dst", f"{abbr.lower()} d st"}
    if slug:
        pretty = slug.replace("_", " ")
        names.add(pretty)
        names.add(f"{pretty} dst")
        names.add(f"{pretty} d st")
        city = pretty.rsplit(" ", 1)[0] if " " in pretty else pretty
        names.add(f"{city} dst")
    return {normalize_name(n) for n in names if n}


class PlayerResolver:
    def __init__(self, dimension: Iterable[PlayerDimRow]):
        self._by_espn: dict[str, list[PlayerDimRow]] = {}
        self._by_name_pos: dict[tuple[str, str], list[PlayerDimRow]] = {}
        self._by_name: dict[str, list[PlayerDimRow]] = {}
        self._dst_by_alias: dict[str, list[PlayerDimRow]] = {}
        for row in dimension:
            if row.espn_player_id:
                self._by_espn.setdefault(row.espn_player_id, []).append(row)
            name = normalize_name(row.player_name)
            pos = row.position
            if name:
                self._by_name.setdefault(name, []).append(row)
                if pos:
                    self._by_name_pos.setdefault((name, pos), []).append(row)
            if pos == "DST" and row.team:
                for alias in _dst_aliases(row.team):
                    self._dst_by_alias.setdefault(alias, []).append(row)

    def resolve(
        self,
        *,
        espn_player_id: str,
        player_name: str,
        position: str,
        team: str,
    ) -> tuple[Optional[str], str, Optional[str]]:
        eid = str(espn_player_id or "").strip()
        if eid:
            hits = _unique(self._by_espn.get(eid, []))
            if len(hits) == 1:
                return hits[0].player_id, RESOLUTION_RESOLVED, None
            if len(hits) > 1:
                return None, RESOLUTION_AMBIGUOUS, "duplicate_espn_player_id"

        pos = str(position or "").strip().upper()
        name = normalize_name(player_name)
        if pos == "DST":
            aliases = _dst_aliases(team)
            if name:
                aliases.add(name)
            dst_hits: list[PlayerDimRow] = []
            for alias in aliases:
                dst_hits.extend(self._dst_by_alias.get(alias, []))
            unique_dst = _unique(dst_hits)
            if len(unique_dst) == 1:
                return unique_dst[0].player_id, RESOLUTION_RESOLVED, "dst_team"
            if len(unique_dst) > 1:
                return None, RESOLUTION_AMBIGUOUS, "ambiguous_dst"

        if name and pos:
            hits = _unique(self._by_name_pos.get((name, pos), []))
            if len(hits) == 1:
                return hits[0].player_id, RESOLUTION_RESOLVED, "name_position"
            if len(hits) > 1:
                return None, RESOLUTION_AMBIGUOUS, "ambiguous_name_position"

        if name:
            hits = _unique(self._by_name.get(name, []))
            if len(hits) == 1:
                return hits[0].player_id, RESOLUTION_RESOLVED, "name_only"
            if len(hits) > 1:
                return None, RESOLUTION_AMBIGUOUS, "ambiguous_name"

        return None, RESOLUTION_UNRESOLVED, "no_match"


def _unique(rows: list[PlayerDimRow]) -> list[PlayerDimRow]:
    seen: set[str] = set()
    out: list[PlayerDimRow] = []
    for row in rows:
        if row.player_id in seen:
            continue
        seen.add(row.player_id)
        out.append(row)
    return out


def resolve_picks(
    picks: list[MappedPick],
    resolver: PlayerResolver,
    report: Optional[ResolutionReport] = None,
) -> list[MappedPick]:
    stats = report or ResolutionReport()
    for pick in picks:
        player_id, status, reason = resolver.resolve(
            espn_player_id=pick.espn_player_id,
            player_name=pick.player_name,
            position=pick.position,
            team=pick.team,
        )
        pick.player_id = player_id
        pick.resolution_status = status
        pick.resolution_reason = None if status == RESOLUTION_RESOLVED else reason
        stats.add(status)
    return picks


def resolve_market(
    rows: list[MappedMarketRow],
    resolver: PlayerResolver,
) -> list[MappedMarketRow]:
    for row in rows:
        player_id, status, _reason = resolver.resolve(
            espn_player_id=row.espn_player_id,
            player_name=row.player_name,
            position=row.position,
            team=row.team,
        )
        row.player_id = player_id if status == RESOLUTION_RESOLVED else None
    return rows


def unresolved_rows(picks: list[MappedPick]) -> list[dict[str, str]]:
    """Every non-resolved pick is persisted; nothing is dropped."""
    out: list[dict[str, str]] = []
    for pick in picks:
        if pick.resolution_status == RESOLUTION_RESOLVED:
            continue
        out.append(
            {
                "espn_player_id": pick.espn_player_id,
                "player_name": pick.player_name,
                "position": pick.position,
                "team": pick.team,
                "season": str(pick.season),
                "draft_id": pick.draft_id,
                "reason": pick.resolution_reason or pick.resolution_status,
                "resolution_status": pick.resolution_status,
            }
        )
    return out
