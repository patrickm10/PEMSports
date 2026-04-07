"""
Sync Rankings from DuckDB to V3 rankings directory.
This serves as the 'Audited Source of Truth' pipeline for the V3 backend.
"""
import logging
from pathlib import Path
import duckdb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sync_v3_rankings")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "rankings"

POSITION_TABLES = {
    "QB": "qb_stats",
    "RB": "rb_stats",
    "WR": "wr_stats",
    "TE": "te_stats",
    "K": "k_stats",
}

def sync_rankings():
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    for pos, table in POSITION_TABLES.items():
        try:
            # Verify table exists
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"Syncing {pos} ({count} rows) from table {table}...")
            
            for suffix in ("seasonal", "weekly"):
                out_path = OUTPUT_DIR / f"{pos}_{suffix}.parquet"
                path_str = str(out_path).replace("\\", "/")
                # Ensure we use the exact table from DuckDB
                conn.execute(f"COPY (SELECT * FROM {table}) TO '{path_str}' (FORMAT PARQUET, COMPRESSION ZSTD)")
                logger.info(f"  OK  {out_path.name}")
                
        except Exception as e:
            logger.error(f"Failed to sync {pos}: {e}")

    conn.close()
    logger.info("Sync complete.")

if __name__ == "__main__":
    sync_rankings()
