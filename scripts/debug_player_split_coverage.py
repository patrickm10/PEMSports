"""
Debug tool: inspect enrichment coverage for player split dimensions.

Usage:
  python scripts/debug_player_split_coverage.py --position wr --player-id <id>
  python scripts/debug_player_split_coverage.py --position wr --player-id <id> --dimension stadium_name

This prints per-year null coverage and top buckets with distinct-year counts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--position", required=True, choices=["qb", "rb", "wr", "te", "k", "dst"])
    p.add_argument("--player-id", required=True)
    p.add_argument(
        "--dimension",
        default="stadium_name",
        choices=["opponent", "stadium_name", "surface_type", "indoor_outdoor"],
    )
    p.add_argument("--db-path", default="data/nfl_stats.db")
    p.add_argument("--top", type=int, default=15)
    args = p.parse_args()

    db_path = Path(args.db_path).resolve()
    con = duckdb.connect(str(db_path), read_only=True)
    table = f"{args.position}_weekly"

    dim = args.dimension

    coverage = con.execute(
        f"""
        SELECT
          CAST(year AS INTEGER) AS year,
          COUNT(*) AS games,
          SUM(CASE WHEN {dim} IS NULL THEN 1 ELSE 0 END) AS dim_null_games
        FROM {table}
        WHERE player_id = ?
        GROUP BY 1
        ORDER BY 1
        """,
        [args.player_id],
    ).fetchall()
    print(f"db_path={db_path}")
    print(f"table={table} player_id={args.player_id} dimension={dim}")
    print("coverage_by_year:", coverage)

    top = con.execute(
        f"""
        SELECT
          {dim} AS key,
          COUNT(*) AS games,
          COUNT(DISTINCT CAST(year AS INTEGER)) AS years,
          MIN(CAST(year AS INTEGER)) AS min_year,
          MAX(CAST(year AS INTEGER)) AS max_year
        FROM {table}
        WHERE player_id = ? AND {dim} IS NOT NULL
        GROUP BY 1
        ORDER BY games DESC
        LIMIT {int(args.top)}
        """,
        [args.player_id],
    ).fetchall()
    print("top_keys:", top)


if __name__ == "__main__":
    main()

