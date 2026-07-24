"""
Enrich data/players.csv with espn_player_id via the Sleeper NFL players dump.

Sleeper exposes a public JSON map of NFL players that includes `espn_id`.
We match on normalized full name + position (and name-only when unique).

Usage (repo root):
  $env:PYTHONPATH="src"
  python scripts/enrich_espn_player_ids.py
  python scripts/bake_db.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("enrich_espn_player_ids")

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
USER_AGENT = "PEMSports-enrich_espn_player_ids/1.0"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize_name(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Drop generational / suffix tokens that often differ across data sources.
    parts = [p for p in s.split(" ") if p not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    return " ".join(parts).strip()


def _load_sleeper_players(*, timeout: int) -> dict[str, Any]:
    resp = requests.get(
        SLEEPER_PLAYERS_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected Sleeper players payload (expected object map).")
    return data


def _build_sleeper_indexes(
    sleeper: dict[str, Any],
) -> tuple[dict[tuple[str, str], list[str]], dict[str, list[str]]]:
    by_name_pos: dict[tuple[str, str], list[str]] = {}
    by_name: dict[str, list[str]] = {}

    for raw in sleeper.values():
        if not isinstance(raw, dict):
            continue
        espn_id = raw.get("espn_id")
        if espn_id is None or str(espn_id).strip() == "":
            continue
        eid = str(espn_id).strip()
        full_name = raw.get("full_name") or ""
        if not full_name and (raw.get("first_name") or raw.get("last_name")):
            full_name = f"{raw.get('first_name') or ''} {raw.get('last_name') or ''}".strip()
        name = normalize_name(full_name)
        if not name:
            continue
        pos = str(raw.get("position") or "").strip().upper()
        by_name.setdefault(name, []).append(eid)
        if pos:
            by_name_pos.setdefault((name, pos), []).append(eid)

    # Deduplicate while preserving order
    def uniq(ids: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    by_name_pos = {k: uniq(v) for k, v in by_name_pos.items()}
    by_name = {k: uniq(v) for k, v in by_name.items()}
    return by_name_pos, by_name


def enrich_players_csv(
    *,
    players_csv: Path,
    timeout: int = 60,
    overwrite: bool = False,
) -> dict[str, int]:
    if not players_csv.exists():
        raise FileNotFoundError(f"Missing players CSV: {players_csv}")

    with open(players_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"No rows in {players_csv}")

    fieldnames = list(rows[0].keys())
    if "espn_player_id" not in fieldnames:
        fieldnames.append("espn_player_id")

    sleeper = _load_sleeper_players(timeout=timeout)
    by_name_pos, by_name = _build_sleeper_indexes(sleeper)

    matched = 0
    preserved = 0
    ambiguous = 0
    missing = 0

    for row in rows:
        existing = str(row.get("espn_player_id") or "").strip()
        if existing and not overwrite:
            preserved += 1
            continue

        name = normalize_name(row.get("player_name") or "")
        pos = str(row.get("position") or "").strip().upper()
        hits: list[str] = []
        if name and pos:
            hits = by_name_pos.get((name, pos), [])
        if len(hits) != 1 and name:
            name_hits = by_name.get(name, [])
            if len(name_hits) == 1:
                hits = name_hits

        if len(hits) == 1:
            row["espn_player_id"] = hits[0]
            matched += 1
        elif len(hits) > 1:
            ambiguous += 1
            if not existing:
                row["espn_player_id"] = ""
        else:
            missing += 1
            if not existing:
                row["espn_player_id"] = ""

    tmp = players_csv.with_suffix(players_csv.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    tmp.replace(players_csv)

    report = {
        "total": len(rows),
        "matched": matched,
        "preserved": preserved,
        "ambiguous": ambiguous,
        "missing": missing,
    }
    logger.info(
        "ESPN id enrichment: total=%d matched=%d preserved=%d ambiguous=%d missing=%d",
        report["total"],
        report["matched"],
        report["preserved"],
        report["ambiguous"],
        report["missing"],
    )
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Fill players.csv espn_player_id from Sleeper.")
    p.add_argument(
        "--players-csv",
        type=Path,
        default=_repo_root() / "data" / "players.csv",
        help="Path to players.csv",
    )
    p.add_argument("--timeout", type=int, default=60, help="HTTP timeout for Sleeper fetch")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing espn_player_id values when a unique match is found",
    )
    args = p.parse_args()

    try:
        enrich_players_csv(
            players_csv=args.players_csv,
            timeout=max(5, args.timeout),
            overwrite=args.overwrite,
        )
    except (OSError, RuntimeError, requests.RequestException) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
