"""
Deterministic completeness validator for NFLStatsAnalyzer.

Scope:
- Validate the committed Parquet sources under data/rankings/.
- Optionally validate the baked DuckDB serving DB (data/nfl_stats.db or NFL_STATS_DB_PATH).

Output:
- Single JSON document to stdout (CI-friendly).
- Exit code 0 on pass, 1 on validation failure, 2 on unexpected error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RANKINGS_DIR = PROJECT_ROOT / "data" / "rankings"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"

# Grounded in src/pipelines/get_weekly_rankings.py
EXPECTED_YEARS = list(range(2020, 2026))  # 2020..2025 inclusive
EXPECTED_WEEKS = list(range(1, 19))  # 1..18 inclusive


@dataclass(frozen=True)
class Failure:
    type: str
    classification: str  # ingestion | transformation | baking
    subject: str  # table name or parquet path
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "classification": self.classification,
            "subject": self.subject,
            "details": self.details,
        }


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)


def _discover_parquets() -> dict[str, dict[str, Path]]:
    """
    Returns {pos: {"weekly": Path|None, "seasonal": Path|None}} for files present.
    Positions are inferred from filenames like QB_weekly.parquet.
    """
    out: dict[str, dict[str, Path]] = {}
    if not RANKINGS_DIR.exists():
        return out

    for p in sorted(RANKINGS_DIR.glob("*.parquet")):
        stem = p.stem  # e.g. QB_weekly
        if not (stem.endswith("_weekly") or stem.endswith("_seasonal")):
            continue
        pos, kind = stem.split("_", 1)
        kind = kind.lower()
        out.setdefault(pos.upper(), {})
        out[pos.upper()][kind] = p
    return out


def _duckdb_range_expected_year_week_sql() -> str:
    # Produces rows (year, week) for all expected combos.
    # DuckDB uses range(start, stop) with stop exclusive.
    return """
      SELECT y.year, w.week
      FROM range(?, ?) AS y(year)
      CROSS JOIN range(?, ?) AS w(week)
    """.strip()


def _missing_week_pairs_sql(source_sql: str) -> str:
    # source_sql must yield year, week
    return f"""
      WITH expected AS (
        {_duckdb_range_expected_year_week_sql()}
      ),
      present AS (
        SELECT DISTINCT CAST(year AS INTEGER) AS year, CAST(week AS INTEGER) AS week
        FROM ({source_sql})
      )
      SELECT expected.year, expected.week
      FROM expected
      LEFT JOIN present USING (year, week)
      WHERE present.year IS NULL
      ORDER BY expected.year, expected.week
    """.strip()


def _missing_years_sql(source_sql: str) -> str:
    return """
      WITH expected AS (
        SELECT year
        FROM range(?, ?) AS y(year)
      ),
      present AS (
        SELECT DISTINCT CAST(year AS INTEGER) AS year
        FROM ({source_sql})
      )
      SELECT expected.year
      FROM expected
      LEFT JOIN present USING (year)
      WHERE present.year IS NULL
      ORDER BY expected.year
    """.format(source_sql=source_sql).strip()


def _columns_for_query(conn: duckdb.DuckDBPyConnection, source_sql: str) -> set[str]:
    cols = [d[0] for d in conn.execute(f"SELECT * FROM ({source_sql}) LIMIT 0").description]
    return {c.lower() for c in cols}


def _null_counts_sql(source_sql: str, cols: set[str]) -> str | None:
    # Only check fields that exist; do not assume "position" exists.
    checks: list[str] = ["COUNT(*) AS rows"]
    if "year" in cols:
        checks.append("SUM(year IS NULL) AS year_nulls")
    if "week" in cols:
        checks.append("SUM(week IS NULL) AS week_nulls")
    if "player_id" in cols:
        checks.append("SUM(player_id IS NULL OR TRIM(CAST(player_id AS VARCHAR)) = '') AS player_id_nulls")
    if "player_name" in cols:
        checks.append("SUM(player_name IS NULL OR TRIM(CAST(player_name AS VARCHAR)) = '') AS player_name_nulls")
    if "team" in cols:
        checks.append("SUM(team IS NULL OR TRIM(CAST(team AS VARCHAR)) = '') AS team_nulls")
    if "fpts_ppr" in cols:
        checks.append("SUM(fpts_ppr IS NULL) AS fpts_ppr_nulls")

    if len(checks) <= 1:
        return None

    return f"SELECT {', '.join(checks)} FROM ({source_sql})"


def _classify_source_issues(
    *,
    failures: list[Failure],
    kind: str,
    subject: str,
    is_weekly: bool,
    cols: set[str],
    required_cols: Iterable[str],
    null_counts: dict[str, Any] | None,
    missing_pairs: list[tuple[int, int]] | None,
    missing_years: list[int] | None,
) -> None:
    # Transformation: missing required columns.
    missing_cols = sorted([c for c in required_cols if c not in cols])
    if missing_cols:
        failures.append(
            Failure(
                type="missing_required_columns",
                classification="transformation",
                subject=subject,
                details={"kind": kind, "missing_columns": missing_cols},
            )
        )

    # Ingestion: missing expected coverage in the Parquet/table itself.
    if missing_pairs:
        failures.append(
            Failure(
                type="missing_year_week",
                classification="ingestion",
                subject=subject,
                details={"missing": [{"year": y, "week": w} for (y, w) in missing_pairs]},
            )
        )
    if missing_years:
        failures.append(
            Failure(
                type="missing_year",
                classification="ingestion",
                subject=subject,
                details={"missing_years": missing_years},
            )
        )

    # Transformation: critical nulls (only for columns that exist).
    if null_counts:
        # We treat any nulls in key identifiers as transformation failures.
        critical_null_keys = ["year_nulls", "player_id_nulls", "player_name_nulls", "team_nulls"]
        if is_weekly:
            critical_null_keys.insert(1, "week_nulls")
        critical = {k: int(null_counts.get(k, 0) or 0) for k in critical_null_keys if k in null_counts}
        if any(v > 0 for v in critical.values()):
            failures.append(
                Failure(
                    type="critical_nulls",
                    classification="transformation",
                    subject=subject,
                    details={"nulls": critical},
                )
            )


def _read_missing_pairs(conn: duckdb.DuckDBPyConnection, source_sql: str) -> list[tuple[int, int]]:
    sql = _missing_week_pairs_sql(source_sql)
    params = [EXPECTED_YEARS[0], EXPECTED_YEARS[-1] + 1, EXPECTED_WEEKS[0], EXPECTED_WEEKS[-1] + 1]
    rows = conn.execute(sql, params).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def _read_missing_years(conn: duckdb.DuckDBPyConnection, source_sql: str) -> list[int]:
    sql = _missing_years_sql(source_sql)
    params = [EXPECTED_YEARS[0], EXPECTED_YEARS[-1] + 1]
    rows = conn.execute(sql, params).fetchall()
    return [int(r[0]) for r in rows]


def _read_null_counts(conn: duckdb.DuckDBPyConnection, source_sql: str, cols: set[str]) -> dict[str, Any] | None:
    sql = _null_counts_sql(source_sql, cols)
    if not sql:
        return None
    cur = conn.execute(sql)
    colnames = [d[0].lower() for d in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return {colnames[i]: row[i] for i in range(len(colnames))}


def _table_name_from_parquet(parquet_path: Path) -> str:
    # e.g. data/rankings/QB_weekly.parquet -> qb_weekly
    return parquet_path.stem.lower()


def validate(*, mode: str, db_path: Path) -> dict[str, Any]:
    failures: list[Failure] = []
    parquets = _discover_parquets()

    # Mode: parquet | duckdb | both
    if mode not in {"parquet", "duckdb", "both"}:
        raise ValueError(f"Invalid mode: {mode}")

    # Always use a separate connection for Parquet scans.
    mem = duckdb.connect(database=":memory:")

    if not parquets:
        failures.append(
            Failure(
                type="missing_parquet_sources",
                classification="ingestion",
                subject=str(RANKINGS_DIR),
                details={"message": "No *_{weekly,seasonal}.parquet files found under data/rankings/."},
            )
        )

    parquet_summaries: dict[str, Any] = {}

    for pos, kinds in parquets.items():
        for kind, p in kinds.items():
            source_sql = f"SELECT * FROM read_parquet('{str(p).replace('\\', '/')}')"
            cols = _columns_for_query(mem, source_sql)
            required = ["year", "player_id", "player_name", "team"]
            if kind == "weekly":
                required = ["year", "week", "player_id", "player_name", "team"]
            # fpts_ppr is used by query engine ordering; only enforce if present.
            missing_pairs = _read_missing_pairs(mem, source_sql) if kind == "weekly" and "year" in cols and "week" in cols else []
            missing_years = _read_missing_years(mem, source_sql) if kind == "seasonal" and "year" in cols else []
            null_counts = _read_null_counts(mem, source_sql, cols)

            _classify_source_issues(
                failures=failures,
                kind=f"parquet_{kind}",
                subject=str(p),
                is_weekly=(kind == "weekly"),
                cols=cols,
                required_cols=required,
                null_counts=null_counts,
                missing_pairs=missing_pairs,
                missing_years=missing_years,
            )

            parquet_summaries[p.name] = {
                "position": pos,
                "kind": kind,
                "columns": sorted(cols),
                "missing_year_week": [{"year": y, "week": w} for (y, w) in missing_pairs] if missing_pairs else [],
                "missing_years": missing_years if missing_years else [],
                "null_counts": null_counts or {},
            }

    mem.close()

    db_summary: dict[str, Any] = {"checked": False}
    if mode in {"duckdb", "both"}:
        if not db_path.exists():
            failures.append(
                Failure(
                    type="duckdb_missing",
                    classification="baking",
                    subject=str(db_path),
                    details={"message": "DuckDB serving DB not found. Run scripts/bake_db.py."},
                )
            )
        else:
            db_summary["checked"] = True
            db = duckdb.connect(str(db_path), read_only=True)
            tables = {r[0] for r in db.execute("SHOW TABLES").fetchall()}
            db_summary["tables"] = sorted(tables)

            for pos, kinds in parquets.items():
                for kind, p in kinds.items():
                    table = _table_name_from_parquet(p)
                    if table not in tables:
                        failures.append(
                            Failure(
                                type="missing_table_for_parquet",
                                classification="baking",
                                subject=table,
                                details={"parquet": str(p)},
                            )
                        )
                        continue

                    source_sql = f"SELECT * FROM {table}"
                    cols = _columns_for_query(db, source_sql)
                    required = ["year", "player_id", "player_name", "team"]
                    if kind == "weekly":
                        required = ["year", "week", "player_id", "player_name", "team"]

                    missing_pairs = _read_missing_pairs(db, source_sql) if kind == "weekly" and "year" in cols and "week" in cols else []
                    missing_years = _read_missing_years(db, source_sql) if kind == "seasonal" and "year" in cols else []
                    null_counts = _read_null_counts(db, source_sql, cols)

                    _classify_source_issues(
                        failures=failures,
                        kind=f"duckdb_{kind}",
                        subject=table,
                        is_weekly=(kind == "weekly"),
                        cols=cols,
                        required_cols=required,
                        null_counts=null_counts,
                        missing_pairs=missing_pairs,
                        missing_years=missing_years,
                    )

                    # Baking regression check: DB must not be less complete than its Parquet.
                    parquet_key = p.name
                    parquet_missing_pairs = parquet_summaries.get(parquet_key, {}).get("missing_year_week", [])
                    parquet_missing_years = parquet_summaries.get(parquet_key, {}).get("missing_years", [])
                    if kind == "weekly" and not parquet_missing_pairs and missing_pairs:
                        failures.append(
                            Failure(
                                type="duckdb_less_complete_than_parquet",
                                classification="baking",
                                subject=table,
                                details={
                                    "parquet": str(p),
                                    "duckdb_missing": [{"year": y, "week": w} for (y, w) in missing_pairs],
                                },
                            )
                        )
                    if kind == "seasonal" and not parquet_missing_years and missing_years:
                        failures.append(
                            Failure(
                                type="duckdb_less_complete_than_parquet",
                                classification="baking",
                                subject=table,
                                details={"parquet": str(p), "duckdb_missing_years": missing_years},
                            )
                        )

            db.close()

    report = {
        "status": "pass" if not failures else "fail",
        "mode": mode,
        "project_root": str(PROJECT_ROOT),
        "rankings_dir": str(RANKINGS_DIR),
        "expected": {"years": EXPECTED_YEARS, "weeks": EXPECTED_WEEKS},
        "duckdb_path": str(db_path),
        "duckdb": db_summary,
        "parquet": parquet_summaries,
        "failures": [f.to_dict() for f in failures],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Parquet and/or DuckDB completeness.")
    parser.add_argument(
        "--mode",
        choices=["parquet", "duckdb", "both"],
        default="both",
        help="Validation target. CI should typically use 'parquet'.",
    )
    parser.add_argument(
        "--db-path",
        default=os.environ.get("NFL_STATS_DB_PATH", str(DEFAULT_DB_PATH)),
        help="DuckDB path (defaults to NFL_STATS_DB_PATH or data/nfl_stats.db).",
    )
    args = parser.parse_args()

    try:
        report = validate(mode=args.mode, db_path=Path(args.db_path).resolve())
        print(_json_dumps(report))
        return 0 if report["status"] == "pass" else 1
    except Exception as exc:
        err = {
            "status": "error",
            "error": str(exc),
        }
        print(_json_dumps(err))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

