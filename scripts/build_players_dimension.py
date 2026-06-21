"""
Build/maintain the canonical Players dimension keyed by internal UUID `player_id`.

Why this exists:
- Raw rankings parquets currently carry a legacy `player_id` (historically MD5 of name/pos/team).
- The serving layer should expose a stable, system-generated UUID `player_id` decoupled from any
  single external provider (ESPN, GSIS, etc.).

Output:
  data/players.csv

Schema:
  player_id         UUID (canonical)
  legacy_player_id  prior parquet player_id (string)
  player_name       display name (best-effort)
  team              team abbr (best-effort)
  position          position code (best-effort)
  espn_player_id    nullable external id for ESPN headshots (string)
"""

from __future__ import annotations

import argparse
import csv
import logging
import uuid
from pathlib import Path
from typing import Iterable

import duckdb


logger = logging.getLogger("build_players_dimension")

# Fixed namespace for RFC 4122 UUID v5 — same legacy_player_id always yields the same player_id
# across clean builds and deploys (required for /headshots/{player_id}.jpg stability).
PLAYER_ID_NAMESPACE = uuid.UUID("a3f2c891-4e7b-5d6c-9a1e-2b8f4c0d3e71")


def _deterministic_player_id(legacy_player_id: str) -> str:
    return str(uuid.uuid5(PLAYER_ID_NAMESPACE, legacy_player_id.strip()))


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_rankings_parquets(rankings_dir: Path) -> Iterable[Path]:
    positions = ["QB", "RB", "WR", "TE", "K", "DST"]
    for pos in positions:
        for suffix in ("weekly", "seasonal"):
            p = rankings_dir / f"{pos}_{suffix}.parquet"
            if p.exists():
                yield p


def _collect_legacy_players(rankings_dir: Path) -> list[dict[str, str]]:
    """
    Collect distinct legacy player ids + light metadata from existing parquets.

    Note: This is allowed to use legacy ids + metadata as bootstrap. The canonical
    key we emit is a new UUID and is what downstream systems should use.
    """
    con = duckdb.connect(database=":memory:")
    try:
        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for pq in _iter_rankings_parquets(rankings_dir):
            path_str = str(pq).replace("\\", "/")
            # Prefer stable names if present; fall back to nulls.
            q = f"""
            SELECT DISTINCT
              CAST(player_id AS VARCHAR) AS legacy_player_id,
              CAST(player_name AS VARCHAR) AS player_name,
              CAST(team AS VARCHAR) AS team,
              CAST(position AS VARCHAR) AS position
            FROM read_parquet('{path_str}')
            WHERE player_id IS NOT NULL
            """
            try:
                for legacy_id, name, team, pos in con.execute(q).fetchall():
                    lid = (legacy_id or "").strip()
                    if not lid or lid in seen:
                        continue
                    seen.add(lid)
                    rows.append(
                        {
                            "legacy_player_id": lid,
                            "player_name": (name or "").strip(),
                            "team": (team or "").strip(),
                            "position": (pos or "").strip(),
                        }
                    )
            except Exception as exc:  # noqa: BLE001 - parquet schema varies across builds
                logger.warning("Skip %s due to read error: %s", pq.name, exc)
                continue
        return sorted(rows, key=lambda r: r["legacy_player_id"])
    finally:
        con.close()


def build_players_csv(*, rankings_dir: Path, out_csv: Path) -> dict[str, int]:
    """
    Create or update data/players.csv.

    - Assigns player_id deterministically via UUID5(namespace, legacy_player_id).
    - Preserves espn_player_id and other enrichments from an existing CSV when present.
    """
    existing_by_legacy: dict[str, dict[str, str]] = {}
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lid = (r.get("legacy_player_id") or "").strip()
                pid = (r.get("player_id") or "").strip()
                if lid and pid:
                    existing_by_legacy[lid] = dict(r)

    discovered = _collect_legacy_players(rankings_dir)

    enriched = 0
    created = 0
    merged: list[dict[str, str]] = []
    for r in discovered:
        lid = r["legacy_player_id"]
        pid = _deterministic_player_id(lid)
        if lid in existing_by_legacy:
            row = existing_by_legacy[lid]
            row["player_id"] = pid
            row["player_name"] = r.get("player_name", row.get("player_name", ""))
            row["team"] = r.get("team", row.get("team", ""))
            row["position"] = r.get("position", row.get("position", ""))
            enriched += 1
        else:
            row = {
                "player_id": pid,
                "legacy_player_id": lid,
                "player_name": r.get("player_name", ""),
                "team": r.get("team", ""),
                "position": r.get("position", ""),
                "espn_player_id": "",
            }
            created += 1
        merged.append(row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "player_id",
        "legacy_player_id",
        "player_name",
        "team",
        "position",
        "espn_player_id",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in sorted(merged, key=lambda x: x["legacy_player_id"]):
            w.writerow({k: (row.get(k) or "") for k in fieldnames})

    return {"discovered": len(discovered), "enriched": enriched, "created": created}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Build data/players.csv keyed by UUID player_id.")
    p.add_argument(
        "--rankings-dir",
        type=Path,
        default=_repo_root() / "data" / "rankings",
        help="Directory containing positional rankings parquets (QB_weekly.parquet, etc.).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=_repo_root() / "data" / "players.csv",
        help="Output CSV path (default: data/players.csv).",
    )
    args = p.parse_args()

    stats = build_players_csv(rankings_dir=args.rankings_dir, out_csv=args.out)
    logger.info(
        "players.csv updated: discovered=%d enriched=%d created=%d -> %s",
        stats["discovered"],
        stats["enriched"],
        stats["created"],
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

