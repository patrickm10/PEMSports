import polars as pl
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def build_ml_features(pos: str, year: Optional[int] = None) -> pl.DataFrame:
    """
    Consolidates Strategy B Parquet data into a flattened training set 
    with situational and momentum features.
    """
    pos = pos.upper()
    path = f"data/rankings/{pos}_weekly.parquet"
    
    if not os.path.exists(path):
        logger.error(f"Source file not found: {path}. Run ingest pipelines first.")
        return pl.DataFrame()

    df = pl.read_parquet(path)
    
    if df.is_empty():
        return df

    # 1. Standardize and Sort for Window Functions
    df = df.sort(["player_id", "year", "week"])

    # 2. Add Rolling Momentum Features (3-Game Windows)
    # Using 'over' player_id to ensure stats don't bleed between players
    momentum_cols = ["fpts", "fpts_ppr"]
    
    # Specific stats per position if available
    pos_specific = {
        "QB": ["pass_yds", "pass_td"],
        "RB": ["rush_yds", "rush_td", "targets"],
        "WR": ["rec_yds", "rec_td", "targets"],
        "TE": ["rec_yds", "rec_td", "targets"]
    }
    
    cols_to_roll = momentum_cols + pos_specific.get(pos, [])
    available_cols = [c for c in cols_to_roll if c in df.columns]

    df = df.with_columns([
        pl.col(c).cast(pl.Float64)
          .rolling_mean(window_size=3, min_periods=1)
          .over("player_id")
          .alias(f"{c}_rolling_3")
        for c in available_cols
    ])

    # 3. Situational Delta (Target Variable)
    # Target = Actual Points - Seasonal Average (Baseline)
    df = df.with_columns([
        pl.col("fpts").mean().over(["player_id", "year"]).alias("season_avg_fpts")
    ])
    
    df = df.with_columns([
        (pl.col("fpts") - pl.col("season_avg_fpts")).alias("points_delta")
    ])

    # 4. Filter for training (optional year filter)
    if year:
        df = df.filter(pl.col("year") == year)

    logger.info(f"Generated {len(df.columns)} features for {pos} ({len(df)} rows)")
    return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test for QB
    test_df = build_ml_features("QB")
    print(test_df.head())
