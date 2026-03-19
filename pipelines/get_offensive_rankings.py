"""
NFL Offensive Rankings orchestrator
Builds standardized rank mappings and writes strict valid dataset.
"""

import logging
import os
import time
from datetime import datetime
import polars as pl
from typing import Dict, Any

from pipelines.constants import OFFENSIVE_POSITIONS
from pipelines.scrapers.fantasypros import scrape_positional_stats
from pipelines.transforms.player_stats import clean_player_data
from pipelines.features.scoring import apply_scoring_features

# Use our new production logger
from pipelines.logger import get_pipeline_logger, PipelineTimer

logger = get_pipeline_logger("offensive_pipeline")

DEFAULT_TOP_N = 10
START_YEAR = 2020
END_YEAR = 2027
OUTPUT_DIR = "data/official_rankings/position"
ARCHIVE_DIR = "data/official_rankings/archive"

# Expected strict schema columns
EXPECTED_SCHEMA = [
    "year", "player_id", "player_name", "team", "position",
    "games_played", "fpts", "fpts_ppr", "fpts_per_game", "fpts_ppr_per_game"
]

def assert_schema_valid(df: pl.DataFrame, pos: str, year: int) -> pl.DataFrame:
    """Strict execution boundaries. Loudly fails if data is corrupted."""
    assert not df.is_empty(), f"{pos} {year} produced an empty dataframe."
    
    missing_cols = [c for c in EXPECTED_SCHEMA if c not in df.columns]
    assert not missing_cols, f"Missing strict columns in {pos} {year}: {missing_cols}"
    
    assert df["fpts"].is_not_null().all(), f"Found null FPTS in {pos} {year}."
    assert df["fpts_ppr"].is_not_null().all(), f"Found null FPTS_PPR in {pos} {year}."
    
    # Return normalized ordering of strict columns
    extra_cols = [c for c in df.columns if c not in EXPECTED_SCHEMA]
    return df.select(EXPECTED_SCHEMA + extra_cols)

def get_positional_rankings(position: str, year: int) -> pl.DataFrame:
    """
    Scrape, clean, and score offensive positional data.
    """
    raw_df = scrape_positional_stats(position, year)
    if raw_df.is_empty():
        return raw_df

    df = clean_player_data(raw_df, position, year)
    df = apply_scoring_features(df, position)
    
    # Fails loudly on schema mismatch
    return assert_schema_valid(df, position, year)

def get_top_rankings_data(df: pl.DataFrame, position: str, top_n: int = DEFAULT_TOP_N) -> Dict[str, Any]:
    """Provide dynamically processed dictionary endpoint grouped top perfomers strictly"""
    if df.is_empty() or "fpts_ppr" not in df.columns:
        return {"position": position, "seasons": {}}
        
    ranked_df = (
        df.filter(pl.col("fpts_ppr").is_not_null())
        .with_columns([
            pl.col("fpts_ppr").rank("dense", descending=True).over("year").alias("rank")
        ])
        .filter(pl.col("rank") <= top_n)
        .sort(["year", "rank"])
    )
    
    result = {"position": position, "seasons": {}}
    years = ranked_df["year"].unique().sort(descending=True)
    
    for year in years:
        year_data = ranked_df.filter(pl.col("year") == year)
        players = []
        for row in year_data.iter_rows(named=True):
            players.append({
                "rank": int(row["rank"]),
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "team": row["team"] or "—",
                "fpts_ppr": round(float(row["fpts_ppr"]), 1),
                "fpts_ppr_per_game": round(float(row["fpts_ppr_per_game"]), 1)
            })
        result["seasons"][str(year)] = players
        
    return result

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with PipelineTimer("offensive_historical_rankings", logger):
        for pos in OFFENSIVE_POSITIONS:
            frames = []
            for year in range(START_YEAR, END_YEAR):
                try:
                    df = get_positional_rankings(pos, year)
                    if not df.is_empty():
                        frames.append(df)
                except AssertionError as e:
                    logger.error("Data Quality Assertion Failed for %s %d: %s", pos, year, e)
                    # Fail loudly on corrupted schema
                    raise

            if not frames:
                logger.warning("No data generated for %s. Skipping save.", pos)
                continue

            combined = pl.concat(frames)

            # Standard deterministic sort: Best seasons historically over fpts_ppr
            combined = combined.sort(["year", "fpts_ppr"], descending=[False, True])
            
            # Paths
            out_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"{pos}_historical.csv"))
            parquet_path = os.path.abspath(os.path.join(OUTPUT_DIR, f"{pos}_historical.parquet"))
            archive_path = os.path.abspath(os.path.join(ARCHIVE_DIR, f"{pos}_historical_{run_timestamp}.csv"))
            
            # Write Standard State
            combined.write_csv(out_path)
            combined.write_parquet(parquet_path)
            # Write Versioned Archive
            combined.write_csv(archive_path)
            
            metrics = {
                "position": pos,
                "rows_processed": len(combined),
                "output_path": out_path,
                "archive_path": archive_path
            }
            logger.info(
                f"Successfully persisted {len(combined)} {pos} records.", 
                extra={"pipeline_metrics": metrics}
            )

if __name__ == "__main__":
    main()
