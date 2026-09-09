"""
NFL Weekly Rankings orchestrator — FantasyPros Scraper Integration.
Builds standardized weekly rank mappings using FantasyPros stats.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import polars as pl
from typing import List
import concurrent.futures

# Ensure 'src' is in sys.path for absolute imports like 'from pipelines...'
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipelines.constants import OFFENSIVE_POSITIONS
from pipelines.logger import get_pipeline_logger, PipelineTimer
from pipelines.transforms.get_new_nfl_data import get_fantasypros_data
from pipelines.enrichment import enrich_weekly_stats

logger = get_pipeline_logger("weekly_pipeline_fantasypros")

# Range to process
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
WEEKS = list(range(1, 19))
OUTPUT_DIR = Path("data/rankings")
LOCAL_RAW_DIR = Path("data_local/raw_scrapes")

CORE_ENRICHMENT_COLS = [
    "opponent", "stadium_name", "city", "state", "indoor_outdoor", "surface_type", "elevation",
    "temp", "humidity", "wind", "game_result", "home_away",
]

def main(years: list[int] | None = None, weeks: list[int] | None = None) -> None:
    years = years or YEARS
    weeks = weeks or WEEKS
    scoped = years != YEARS or weeks != WEEKS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    with PipelineTimer("weekly_rankings_fantasypros", logger):
        for pos in OFFENSIVE_POSITIONS + ["DST"]:
            all_weeks_data = []
            
            def fetch_week(year, week):
                try:
                    df = get_fantasypros_data(pos, year, week=week)
                    if not df.is_empty():
                        df = df.with_columns(pl.lit(week, dtype=pl.Int64).alias("week"))
                        df = enrich_weekly_stats(df)
                        
                        # Save raw CSV for backup
                        csv_name = f"{pos}_{year}_W{week}.csv"
                        df.write_csv(LOCAL_RAW_DIR / csv_name)
                        
                        return df
                except Exception as e:
                    logger.error(f"Failed to fetch {pos} for {year} week {week}: {e}")
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for year in years:
                    for week in weeks:
                        futures.append(executor.submit(fetch_week, year, week))
                
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res is not None:
                        all_weeks_data.append(res)
            
            if not all_weeks_data:
                logger.error(f"No weekly data fetched for position {pos}")
                continue
                
            combined_df = pl.concat(all_weeks_data, how="diagonal")
            
            # Ensure core enrichment columns exist
            for col in CORE_ENRICHMENT_COLS:
                if col not in combined_df.columns:
                    combined_df = combined_df.with_columns(pl.lit(None).alias(col))
            
            out_parquet = OUTPUT_DIR / f"{pos}_weekly.parquet"
            if scoped and out_parquet.exists():
                existing = pl.read_parquet(out_parquet)
                drop_keys = combined_df.select(["year", "week"]).unique()
                if "year" in existing.columns and "week" in existing.columns:
                    existing = existing.join(drop_keys, on=["year", "week"], how="anti")
                combined_df = pl.concat([existing, combined_df], how="diagonal")
                logger.info(
                    "Merged %s weekly scrape into existing parquet (%d rows)",
                    pos,
                    combined_df.height,
                )

            final_df = combined_df.sort(["year", "week", "fpts_ppr"], descending=[True, True, True])
            final_df.write_parquet(out_parquet)
            
            logger.info("Saved consolidated %s Weekly to %s", pos, out_parquet)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape FantasyPros weekly rankings.")
    parser.add_argument("--year", type=int, default=None, help="Single season year (default: 2020-2025).")
    parser.add_argument("--week", type=int, default=None, help="Single week 1-18 (default: all weeks).")
    args = parser.parse_args()
    years = [args.year] if args.year is not None else None
    weeks = [args.week] if args.week is not None else None
    main(years=years, weeks=weeks)


