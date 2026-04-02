"""
NFL Offensive Rankings orchestrator — FantasyPros Scraper Integration.
Builds standardized rank mappings using FantasyPros seasonal data.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import polars as pl
from typing import List

# Ensure 'src' is in sys.path for absolute imports like 'from pipelines...'
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipelines.constants import OFFENSIVE_POSITIONS
from pipelines.logger import get_pipeline_logger, PipelineTimer
from pipelines.transforms.get_new_nfl_data import get_fantasypros_data
from pipelines.enrichment import get_team_slug, normalize_season

logger = get_pipeline_logger("offensive_pipeline_fantasypros")

# Years requested by user
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
OUTPUT_DIR = "data/official_rankings/position"



def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with PipelineTimer("offensive_historical_rankings_fantasypros", logger):
        for pos in OFFENSIVE_POSITIONS:
            all_years_data = []
            for year in YEARS:
                try:
                    df = get_fantasypros_data(pos, year)
                    if not df.is_empty():
                        # Normalize team and add season
                        df = df.with_columns([
                            pl.col("team").map_elements(get_team_slug, return_dtype=pl.String),
                            pl.lit(normalize_season(year)).alias("season")
                        ])
                        all_years_data.append(df)
                    else:
                        logger.warning(f"No data for {pos} in {year}")
                except Exception as e:
                    logger.error(f"Failed to fetch {pos} for {year}: {e}")
            
            if not all_years_data:
                logger.error(f"No data fetched for position {pos}")
                continue
                
            # Combine all years for this position
            combined_df = pl.concat(all_years_data, how="diagonal")
            
            # Select and sort dynamically
            final_df = combined_df.sort(["year", "fpts_ppr"], descending=[True, True])
            
            out_parquet = os.path.join(OUTPUT_DIR, f"{pos}_historical.parquet")
            out_csv = os.path.join(OUTPUT_DIR, f"{pos}_historical.csv")
            
            final_df.write_parquet(out_parquet)
            final_df.write_csv(out_csv)
            logger.info("Saved %d records for %s Historical", len(final_df), pos)

if __name__ == "__main__":
    main()
