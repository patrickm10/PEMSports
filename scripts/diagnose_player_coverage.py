"""
Diagnose player analytics data coverage from the API.

Goal: quickly answer questions like:
- "Does this player have 17 games in 2025?"
- "Are opponent/stadium charts missing 2025 coverage because weekly rows have null context?"
- "Do split-by-year 'games' totals match weekly played games?"

This script queries the same FastAPI endpoints the frontend uses:
- /api/v1/players/search
- /api/v1/players/{id}/weekly
- /api/v1/players/{id}/splits/{dimension}/by-year

It is intentionally dependency-free (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any, Iterable


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _api_base(origin: str) -> str:
    origin = origin.rstrip("/")
    if origin.endswith("/api/v1"):
        return origin
    return f"{origin}/api/v1"


def _search(api: str, q: str, limit: int = 8) -> list[dict[str, Any]]:
    url = f"{api}/players/search?q={urllib.parse.quote(q)}&limit={limit}"
    payload = _get_json(url)
    return payload.get("results", []) or []


def _weekly(api: str, player_id: str, pos: str) -> dict[str, Any]:
    url = f"{api}/players/{urllib.parse.quote(player_id)}/weekly?pos={urllib.parse.quote(pos)}"
    return _get_json(url)


def _splits_by_year(api: str, player_id: str, pos: str, dim: str) -> dict[str, Any]:
    url = (
        f"{api}/players/{urllib.parse.quote(player_id)}/splits/"
        f"{urllib.parse.quote(dim)}/by-year?pos={urllib.parse.quote(pos)}"
    )
    return _get_json(url)


def _year_block(seasons: Iterable[dict[str, Any]], year: int) -> dict[str, Any] | None:
    for s in seasons:
        if int(s.get("year") or 0) == year:
            return s
    return None


def _sum_games(rows: list[dict[str, Any]], year: int) -> int:
    return sum(int(r.get("games") or 0) for r in rows if int(r.get("year") or 0) == year)


def _weeks_set(weeks: list[dict[str, Any]]) -> set[int]:
    out: set[int] = set()
    for w in weeks:
        try:
            out.add(int(w.get("week")))
        except Exception:
            continue
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000/api/v1", help="API base (default: http://localhost:8000/api/v1)")
    p.add_argument("--q", required=True, help="Search query (player name)")
    p.add_argument("--pos", default="", help="Optional position filter (qb|rb|wr|te|k|dst). If omitted, uses top search hit.")
    p.add_argument("--year", type=int, default=2025, help="Year to focus (default: 2025)")
    p.add_argument("--player-id", default="", help="Optional explicit player_id to skip search")
    args = p.parse_args(argv)

    api = _api_base(args.api)

    try:
        if args.player_id:
            player_id = args.player_id
            pos = args.pos.lower()
            name = args.q
            if not pos:
                print("ERROR: --pos is required when using --player-id", file=sys.stderr)
                return 2
        else:
            hits = _search(api, args.q)
            if not hits:
                print(f"NO_RESULTS: q={args.q!r}", file=sys.stderr)
                return 1
            if args.pos:
                pos_hits = [h for h in hits if str(h.get("position") or "").lower() == args.pos.lower()]
                if pos_hits:
                    hits = pos_hits
            hit = hits[0]
            player_id = str(hit.get("player_id"))
            name = str(hit.get("player_name"))
            pos = str(hit.get("position") or "").lower()

        weekly_payload = _weekly(api, player_id, pos)
        seasons = weekly_payload.get("seasons") or []
        season = _year_block(seasons, args.year)
        weeks = (season or {}).get("weeks") or []

        # Weekly coverage
        week_nums = sorted(_weeks_set(weeks))
        expected = set(range(1, 19))
        missing_weeks = sorted(expected - set(week_nums))

        null_dim_weeks = sorted(
            int(w.get("week"))
            for w in weeks
            if w.get("week") is not None
            and (w.get("opponent") is None or w.get("stadium_name") is None)
        )

        # Splits coverage
        dims = ["opponent", "stadium"]
        splits = {d: _splits_by_year(api, player_id, pos, d) for d in dims}

        # For by-year splits, games should roughly match played games where dim is present.
        # This excludes rows where dim is null (by design), so comparing to weekly null_dim_weeks is the key.
        split_games = {d: _sum_games(splits[d].get("rows") or [], args.year) for d in dims}

        # Print concise report
        print(f"PLAYER: {name} ({pos.upper()}) id={player_id}")
        print(f"YEAR: {args.year}")
        print(f"WEEKLY: weeks_returned={len(weeks)} weeks_present={len(week_nums)} missing_weeks={missing_weeks}")
        print(f"WEEKLY: weeks_with_null_opponent_or_stadium={null_dim_weeks}")
        for d in dims:
            years = splits[d].get("years") or []
            print(f"SPLIT_BY_YEAR[{d}]: years={years} games_sum_{args.year}={split_games[d]}")

        # Quick diagnosis labels
        if not season:
            print("DIAGNOSIS: weekly_missing_year")
        elif missing_weeks:
            print("DIAGNOSIS: weekly_missing_weeks")
        elif null_dim_weeks:
            print("DIAGNOSIS: weekly_has_null_context_weeks -> splits will exclude those weeks")
        else:
            print("DIAGNOSIS: weekly_complete_for_year")

        return 0

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP_ERROR: {e.code} {e.reason} body={body[:500]}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

