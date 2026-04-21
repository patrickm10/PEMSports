import polars as pl
from pathlib import Path
import os
import sys

# Add 'src' to path for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from pipelines.enrichment import get_team_slug

def debug_join_keys():
    # 1. Sample Team Stats (Weekly)
    qb_path = Path("data/rankings/QB_weekly.parquet")
    if qb_path.exists():
        df = pl.read_parquet(qb_path)
        print("--- QB Weekly Raw 'team' values ---")
        print(df["team"].unique().to_list()[:10])
        print("--- QB Weekly Slugs ---")
        print(df["team"].map_elements(get_team_slug, return_dtype=pl.String).unique().to_list()[:10])

    # 2. Sample Matchups
    matchups_path = Path("data/nfl_metadata/nfl_matchups_enriched.csv")
    if matchups_path.exists():
        m = pl.read_csv(matchups_path, infer_schema_length=0)
        print("\n--- Matchups Raw 'Winner' values ---")
        print(m["Winner"].unique().to_list()[:10])
        print("--- Matchups Slugs (from Winner) ---")
        print(m["Winner"].map_elements(get_team_slug, return_dtype=pl.String).unique().to_list()[:10])

    # 3. Check Year/Week types
    if qb_path.exists() and matchups_path.exists():
        print("\n--- Types ---")
        print(f"QB Weekly Year type: {df['year'].dtype}")
        print(f"QB Weekly Week type: {df['week'].dtype}")
        print(f"Matchups Year type: {m['Year'].dtype}")
        print(f"Matchups Week type: {m['Week'].dtype}")

if __name__ == "__main__":
    debug_join_keys()
