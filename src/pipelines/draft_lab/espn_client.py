"""Live ESPN Fantasy JSON client. Tests must not call this (no network)."""

from __future__ import annotations

import os
from typing import Any, Optional

from pipelines.http_client import fetch_json

ESPN_FFL_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
DEFAULT_VIEWS = ("mDraftDetail", "mSettings", "mTeam", "kona_player_info")
USER_AGENT = "PEMSports-draft-lab/1.0"


def espn_cookies_from_env() -> dict[str, str]:
    cookies: dict[str, str] = {}
    s2 = os.getenv("ESPN_S2", "").strip()
    swid = os.getenv("ESPN_SWID", "").strip()
    if s2:
        cookies["espn_s2"] = s2
    if swid:
        cookies["SWID"] = swid
    return cookies


def league_ids_from_env() -> list[str]:
    return [part.strip() for part in os.getenv("ESPN_LEAGUE_IDS", "").split(",") if part.strip()]


def seasons_from_env(*, default: tuple[int, ...] = (2024, 2023, 2022)) -> list[int]:
    raw = os.getenv("ESPN_SEASONS", "").strip()
    if not raw:
        return list(default)
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def fetch_league_season(
    espn_league_id: str,
    season: int,
    *,
    cookies: Optional[dict[str, str]] = None,
    timeout: int = 20,
) -> Optional[Any]:
    """Fetch one season. Tries the season endpoint, then leagueHistory."""
    headers = {"User-Agent": USER_AGENT}
    views = [("view", v) for v in DEFAULT_VIEWS]
    auth = cookies if cookies is not None else espn_cookies_from_env()

    season_url = (
        f"{ESPN_FFL_BASE}/seasons/{season}/segments/0/leagues/{espn_league_id}"
    )
    payload = fetch_json(
        season_url,
        timeout=timeout,
        cookies=auth or None,
        headers=headers,
        params=views,
    )
    if payload is not None:
        return payload

    history_url = f"{ESPN_FFL_BASE}/leagueHistory/{espn_league_id}"
    return fetch_json(
        history_url,
        timeout=timeout,
        cookies=auth or None,
        headers=headers,
        params=[("seasonId", season), *views],
    )


def fetch_live_payloads(
    *,
    league_ids: Optional[list[str]] = None,
    seasons: Optional[list[int]] = None,
    cookies: Optional[dict[str, str]] = None,
    timeout: int = 20,
) -> list[Any]:
    ids = league_ids if league_ids is not None else league_ids_from_env()
    years = seasons if seasons is not None else seasons_from_env()
    if not ids:
        raise ValueError("ESPN_LEAGUE_IDS is empty; pass --league-id or set the env var")
    payloads: list[Any] = []
    for league_id in ids:
        for year in years:
            raw = fetch_league_season(
                league_id, year, cookies=cookies, timeout=timeout
            )
            if raw is None:
                continue
            payloads.append(raw)
    return payloads
