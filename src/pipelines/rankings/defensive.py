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

from pipelines.logger import get_pipeline_logger, PipelineTimer
from pipelines.transforms.get_new_nfl_data import get_fantasypros_data
from pipelines.enrichment import get_team_slug, normalize_season

logger = get_pipeline_logger("defensive_pipeline_fantasypros")

START_YEAR = 2020
END_YEAR = 2027
OUTPUT_DIR = "data/official_rankings/position"


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with PipelineTimer("defensive_historical_rankings_fantasypros", logger):
        years = list(range(START_YEAR, END_YEAR))
        all_years_data = []
        
        for year in years:
            try:
                df = get_fantasypros_data("DST", year)
                if not df.is_empty():
                    # Normalize team and add season
                    df = df.with_columns([
                        pl.col("team").map_elements(get_team_slug, return_dtype=pl.String),
                        pl.lit(normalize_season(year)).alias("season")
                    ])
                    all_years_data.append(df)
                else:
                    logger.warning(f"No DST data for {year}")
            except Exception as e:
                logger.error(f"Failed to fetch DST for {year}: {e}")
        
        if not all_years_data:
            logger.error("No DST data fetched at all.")
            return
            
        combined_df = pl.concat(all_years_data, how="diagonal")
        
        final_df = combined_df.sort(["year", "fpts_ppr"], descending=[True, True])
        
        out_path = os.path.join(OUTPUT_DIR, "DST_historical.csv")
        parquet_path = os.path.join(OUTPUT_DIR, "DST_historical.parquet")
        
        final_df.write_csv(out_path)
        final_df.write_parquet(parquet_path)
        
        logger.info("Successfully persisted %d DST records with normalization.", len(final_df))

if __name__ == "__main__":
    main()
