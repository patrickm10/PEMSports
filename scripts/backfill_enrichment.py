import polars as pl
import os
import sys
from pathlib import Path

# Add 'src' to path for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from pipelines.enrichment import enrich_weekly_stats

def backfill_position(pos):
    parquet_path = Path(f"data/rankings/{pos}_weekly.parquet")
    if not parquet_path.exists():
        print(f"Skipping {pos}: File not found.")
        return

    print(f"Enriching {pos} weekly rankings...")
    df = pl.read_parquet(parquet_path)
    
    # Apply enrichment logic (joins with nfl_matchups_enriched.csv)
    enriched_df = enrich_weekly_stats(df)
    
    # Save back to parquet
    enriched_df.write_parquet(parquet_path)
    print(f"Successfully backfilled {pos}. Row count: {len(enriched_df)}")

def main():
    positions = ["QB", "RB", "WR", "TE", "K", "DST"]
    for pos in positions:
        backfill_position(pos)

if __name__ == "__main__":
    main()
