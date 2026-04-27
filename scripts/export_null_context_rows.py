"""
Export weekly rows with null opponent and/or stadium_name to CSV.

This is meant for quick diagnosis of missing context fields in the baked weekly data.
It queries the same FastAPI endpoint the UI uses:
  /api/v1/players/{player_id}/weekly?pos=...

No third-party dependencies (stdlib only).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _api_base(origin: str) -> str:
    origin = origin.rstrip("/")
    if origin.endswith("/api/v1"):
        return origin
    return f"{origin}/api/v1"


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _search(api: str, q: str, limit: int = 10) -> list[dict[str, Any]]:
    url = f"{api}/players/search?q={urllib.parse.quote(q)}&limit={limit}"
    payload = _get_json(url)
    return payload.get("results", []) or []


def _weekly(api: str, player_id: str, pos: str) -> dict[str, Any]:
    url = f"{api}/players/{urllib.parse.quote(player_id)}/weekly?pos={urllib.parse.quote(pos)}"
    return _get_json(url)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--api",
        default="http://localhost:8000/api/v1",
        help="API base (default: http://localhost:8000/api/v1)",
    )
    p.add_argument("--q", default="", help="Player search query (name). Ignored if --player-id is set.")
    p.add_argument("--player-id", default="", help="Explicit player_id (skips search).")
    p.add_argument("--pos", default="", help="Position (qb|rb|wr|te|k|dst). Required with --player-id.")
    p.add_argument("--year", type=int, default=0, help="Optional year filter (e.g. 2025). 0 = all years.")
    p.add_argument(
        "--out",
        default="null_context_rows.csv",
        help="Output CSV path (default: null_context_rows.csv)",
    )
    args = p.parse_args(argv)

    api = _api_base(args.api)
    year_filter = int(args.year or 0)

    try:
        if args.player_id:
            player_id = args.player_id
            pos = args.pos.lower().strip()
            if not pos:
                print("ERROR: --pos is required when using --player-id", file=sys.stderr)
                return 2
            player_name = args.q or player_id
        else:
            q = args.q.strip()
            if not q:
                print("ERROR: provide --q or --player-id", file=sys.stderr)
                return 2
            hits = _search(api, q, limit=10)
            if not hits:
                print(f"NO_RESULTS: q={q!r}", file=sys.stderr)
                return 1
            if args.pos:
                hits = [h for h in hits if str(h.get("position") or "").lower() == args.pos.lower()] or hits
            hit = hits[0]
            player_id = str(hit.get("player_id"))
            player_name = str(hit.get("player_name") or q)
            pos = str(hit.get("position") or "").lower()

        weekly_payload = _weekly(api, player_id, pos)
        seasons = weekly_payload.get("seasons") or []

        rows: list[dict[str, Any]] = []
        for season in seasons:
            yr = int(season.get("year") or 0)
            if year_filter and yr != year_filter:
                continue
            for w in season.get("weeks") or []:
                opponent = w.get("opponent")
                stadium_name = w.get("stadium_name")
                if opponent is None or stadium_name is None:
                    rows.append(
                        {
                            "player_id": player_id,
                            "player_name": player_name,
                            "position": pos,
                            "year": yr,
                            "week": w.get("week"),
                            "ppr_fpts": w.get("ppr_fpts"),
                            "fantasy_points": w.get("fantasy_points"),
                            "yards": w.get("yards"),
                            "tds": w.get("tds"),
                            "opponent": opponent,
                            "stadium_name": stadium_name,
                            "surface_type": w.get("surface_type"),
                            "indoor_outdoor": w.get("indoor_outdoor"),
                            "weather_impact": w.get("weather_impact"),
                            "temp": w.get("temp"),
                            "humidity": w.get("humidity"),
                            "wind": w.get("wind"),
                        }
                    )

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "player_id",
            "player_name",
            "position",
            "year",
            "week",
            "ppr_fpts",
            "fantasy_points",
            "yards",
            "tds",
            "opponent",
            "stadium_name",
            "surface_type",
            "indoor_outdoor",
            "weather_impact",
            "temp",
            "humidity",
            "wind",
        ]

        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)

        print(
            f"WROTE: {out_path} rows={len(rows)} player={player_name} pos={pos.upper()} id={player_id} year={year_filter or 'ALL'}"
        )
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

