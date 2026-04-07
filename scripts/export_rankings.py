"""
Export DuckDB tables to data/rankings/ Parquet files.

This script reads weekly data from data/nfl_stats.db and writes Parquet files
in the naming convention expected by src/backend/data/query_engine.py:
  data/rankings/{POS}_seasonal.parquet
  data/rankings/{POS}_weekly.parquet

Since the source data is weekly-granular, both seasonal and weekly files
contain the same rows. The query engine's view layer handles ranking and
partitioning.
"""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "rankings"

# Map: position key -> DuckDB table name
POSITION_TABLES = {
    "QB": "qb_stats",
    "RB": "rb_stats",
    "WR": "wr_stats",
    "TE": "te_stats",
    "K": "k_stats",
}


def main() -> int:
    if not DB_PATH.exists():
        print(f"FATAL: Database not found at {DB_PATH}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    errors = []
    for pos, table in POSITION_TABLES.items():
        # Verify table exists and has data
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except duckdb.CatalogException:
            errors.append(f"Table '{table}' does not exist in {DB_PATH}")
            continue

        if count == 0:
            errors.append(f"Table '{table}' is empty")
            continue

        # Export to both seasonal and weekly Parquet (identical content)
        for suffix in ("seasonal", "weekly"):
            out_path = OUTPUT_DIR / f"{pos}_{suffix}.parquet"
            # Use DuckDB COPY for direct, efficient Parquet export
            path_str = str(out_path).replace("\\", "/")
            conn.execute(
                f"COPY (SELECT * FROM {table}) TO '{path_str}' (FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            size_kb = out_path.stat().st_size / 1024
            print(f"  OK  {out_path.name} ({count} rows, {size_kb:.1f} KB)")

    conn.close()

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1

    # Final validation: all 10 files exist with non-zero size
    expected = []
    for pos in POSITION_TABLES:
        for suffix in ("seasonal", "weekly"):
            expected.append(OUTPUT_DIR / f"{pos}_{suffix}.parquet")

    missing = [p for p in expected if not p.exists() or p.stat().st_size == 0]
    if missing:
        print(f"\nVALIDATION FAILED — missing or empty files:")
        for m in missing:
            print(f"  - {m.name}")
        return 1

    print(f"\nSUCCESS: {len(expected)} Parquet files written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
