"""
Validation gate: enforce deterministic headshot coverage keyed by `player_id`.

Rules:
- Canonical player list comes from DuckDB table `players` (baked into data/nfl_stats.db).
- For each player_id, check existence of data/headshots/{player_id}.jpg via direct lookup.
  (No directory scanning is required for the check itself.)
- Fail if coverage < 98%.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb


logger = logging.getLogger("validate_headshots")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_player_ids(db_path: Path) -> list[str]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "players" not in tables:
            raise RuntimeError("Missing `players` table in serving DB.")
        rows = con.execute(
            "SELECT CAST(player_id AS VARCHAR) AS player_id FROM players WHERE player_id IS NOT NULL"
        ).fetchall()
        return sorted({str(r[0]).strip() for r in rows if r and r[0]})
    finally:
        con.close()


def validate(*, db_path: Path, headshots_dir: Path, min_coverage: float) -> dict[str, object]:
    player_ids = _load_player_ids(db_path)
    total = len(player_ids)
    found = 0
    missing: list[str] = []

    for pid in player_ids:
        p = headshots_dir / f"{pid}.jpg"
        if p.exists():
            found += 1
        else:
            missing.append(pid)

    coverage = (found / total) if total else 1.0
    report = {
        "total_players": total,
        "headshots_found": found,
        "missing_headshots": len(missing),
        "coverage": coverage,
        "missing_player_ids": missing[:50],
    }

    logger.info("Players: %d", total)
    logger.info("Headshots found: %d", found)
    logger.info("Missing headshots: %d", len(missing))
    logger.info("Coverage: %.2f%% (min %.2f%%)", coverage * 100.0, min_coverage * 100.0)
    if missing:
        logger.warning("Missing sample (first %d): %s", len(report["missing_player_ids"]), report["missing_player_ids"])

    if coverage < min_coverage:
        raise SystemExit(2)
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Validate headshot coverage keyed by player_id.")
    p.add_argument("--db", type=Path, default=_repo_root() / "data" / "nfl_stats.db", help="Path to nfl_stats.db")
    p.add_argument(
        "--headshots-dir",
        type=Path,
        default=_repo_root() / "data" / "headshots",
        help="Directory containing {player_id}.jpg files",
    )
    p.add_argument(
        "--min-coverage",
        type=float,
        default=0.98,
        help="Fail if found/total is below this ratio (default: 0.98).",
    )
    args = p.parse_args()

    validate(db_path=args.db, headshots_dir=args.headshots_dir, min_coverage=max(0.0, min(1.0, args.min_coverage)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

