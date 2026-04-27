"""
Inspect opponent coverage for a specific player in the baked DuckDB.

Usage (PowerShell):
  python scripts/inspect_player_opponent_coverage.py --pos wr --name "smith-njigba"
  python scripts/inspect_player_opponent_coverage.py --pos wr --player-id <id>
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb


def _db_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    return Path(
        os.environ.get("NFL_STATS_DB_PATH", str(repo_root / "data" / "nfl_stats.db"))
    ).resolve()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pos", required=True, choices=["qb", "rb", "wr", "te", "k", "dst"])
    p.add_argument("--player-id", default=None)
    p.add_argument("--name", default=None, help="case-insensitive substring match")
    p.add_argument("--year", type=int, default=None, help="optional year filter for opponent breakdown")
    p.add_argument(
        "--opponent",
        default=None,
        help="optional opponent slug to count games against (e.g. green_bay_packers)",
    )
    p.add_argument(
        "--since-year",
        type=int,
        default=None,
        help="optional lower bound year (inclusive) for --opponent totals",
    )
    p.add_argument(
        "--through-year",
        type=int,
        default=None,
        help="optional upper bound year (inclusive) for --opponent totals",
    )
    p.add_argument(
        "--weekly-details",
        action="store_true",
        help="when --year is set, print week coverage + null metric counts",
    )
    args = p.parse_args()

    if not args.player_id and not args.name:
        raise SystemExit("Provide --player-id or --name")

    table = f"{args.pos.lower()}_weekly"
    db_path = _db_path()
    if not db_path.exists():
        raise SystemExit(f"DB missing at {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        player_id = args.player_id
        if not player_id:
            q = (args.name or "").strip().lower()
            rows = con.execute(
                f"""
                SELECT player_id, player_name, COUNT(*) AS games
                FROM {table}
                WHERE LOWER(CAST(player_name AS VARCHAR)) LIKE ?
                GROUP BY 1,2
                ORDER BY games DESC
                """,
                [f"%{q}%"],
            ).fetchall()
            print(f"matches={len(rows)}")
            for r in rows[:10]:
                print({"player_id": r[0], "player_name": r[1], "rows": int(r[2])})
            if not rows:
                return 0
            player_id = rows[0][0]

        print(f"db_path={db_path}")
        print(f"table={table}")
        print(f"player_id={player_id}")

        per_year = con.execute(
            f"""
            SELECT
              CAST(year AS INTEGER) AS year,
              COUNT(*) AS rows,
              SUM(opponent IS NULL) AS opponent_nulls
            FROM {table}
            WHERE player_id = ?
            GROUP BY 1
            ORDER BY 1
            """,
            [player_id],
        ).fetchall()
        print("per_year=", [(int(y), int(r), int(n)) for (y, r, n) in per_year])

        if args.opponent:
            conditions = ["player_id = ?", "opponent = ?"]
            params: list[object] = [player_id, args.opponent]
            if args.since_year is not None:
                conditions.append("CAST(year AS INTEGER) >= ?")
                params.append(args.since_year)
            if args.through_year is not None:
                conditions.append("CAST(year AS INTEGER) <= ?")
                params.append(args.through_year)
            where = " AND ".join(conditions)
            total = con.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {where}",
                params,
            ).fetchone()[0]
            print(
                "opponent_total=",
                {
                    "opponent": args.opponent,
                    "since_year": args.since_year,
                    "through_year": args.through_year,
                    "games": int(total),
                },
            )

        yr = args.year
        if yr is not None:
            opp = con.execute(
                f"""
                SELECT opponent, COUNT(*) AS games
                FROM {table}
                WHERE player_id = ? AND CAST(year AS INTEGER) = ?
                GROUP BY 1
                ORDER BY games DESC
                """,
                [player_id, yr],
            ).fetchall()
            print(f"opponent_breakdown_{yr}=", [(o, int(g)) for (o, g) in opp])

            if args.weekly_details:
                # Focus on why line-series points might be missing: missing weeks vs null fpts_ppr.
                weekly = con.execute(
                    f"""
                    SELECT
                      CAST(week AS INTEGER) AS week,
                      fpts_ppr
                    FROM {table}
                    WHERE player_id = ? AND CAST(year AS INTEGER) = ?
                    ORDER BY week
                    """,
                    [player_id, yr],
                ).fetchall()
                weeks = [int(w) for (w, _) in weekly if w is not None]
                null_weeks = [int(w) for (w, v) in weekly if w is not None and v is None]
                missing_weeks = [w for w in range(1, 19) if w not in set(weeks)]
                print(
                    f"weekly_{yr}=",
                    {
                        "rows": len(weekly),
                        "distinct_weeks": len(set(weeks)),
                        "missing_weeks": missing_weeks,
                        "weeks_with_null_fpts_ppr": null_weeks,
                    },
                )
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

