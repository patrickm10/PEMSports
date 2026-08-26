"""
Enrichment utility to add player team, opponent, weather, and stadium metadata to weekly records.
"""

import os
import logging
import polars as pl
from pathlib import Path
from typing import Optional
from pipelines.constants import TEAM_MAP

logger = logging.getLogger(__name__)

# Base paths
BASE_DATA_DIR = Path("data/nfl_metadata")
ROSTER_PATH = BASE_DATA_DIR / "nfl_roster.csv"
ENRICHED_MATCHUPS_PATH = BASE_DATA_DIR / "nfl_matchups_enriched.csv"

def normalize_season(year: int) -> str:
    """Normalize 2024 -> 2024-2025"""
    return f"{year}-{year+1}"

def get_team_slug(team_raw: str) -> str:
    """Convert 'KC' or 'Kansas City Chiefs' to 'kansas_city_chiefs'"""
    if not team_raw:
        return "unknown"
    
    # 1. Check if it's an abbreviation in TEAM_MAP
    up = str(team_raw).upper()
    if up in TEAM_MAP:
        return TEAM_MAP[up]
    
    # 2. Normalize the string to a slug
    slug = str(team_raw).lower().replace(" ", "_").replace(".", "").replace("'", "")
    
    # 3. Handle historical full name variants
    historical_variants = {
        "washington_redskins": "washington_commanders",
        "washington_football_team": "washington_commanders",
        "oakland_raiders": "las_vegas_raiders",
        "san_diego_chargers": "los_angeles_chargers",
        "st_louis_rams": "los_angeles_rams"
    }
    
    return historical_variants.get(slug, slug)

def get_rich_schedule() -> pl.DataFrame:
    """
    Returns a DataFrame mapping (year, week, team) -> (opponent, stadium, weather, etc.)
    using nfl_matchups_enriched.csv.
    """
    if not ENRICHED_MATCHUPS_PATH.exists():
        logger.warning(f"Enriched matchups file not found: {ENRICHED_MATCHUPS_PATH}")
        return pl.DataFrame()

    # Load enriched matchups
    df = pl.read_csv(ENRICHED_MATCHUPS_PATH, infer_schema_length=0)
    
    # Standardize column names and types
    df = df.rename({
        "Week": "week",
        "Year": "year",
        "Winner": "winner",
        "Loser": "loser",
        "Date": "date"
    })
    
    # Explicitly cast join keys to Int64 early
    df = df.with_columns([
        pl.col("year").cast(pl.Int64, strict=False),
        pl.col("week").cast(pl.Int64, strict=False)
    ]).filter(pl.col("year").is_not_null() & pl.col("week").is_not_null())

    # Join weather data
    WEATHER_PATH = BASE_DATA_DIR / "nfl_matchups_with_weather.csv"
    if WEATHER_PATH.exists():
        weather_df = pl.read_csv(WEATHER_PATH, infer_schema_length=0)
        if all(c in weather_df.columns for c in ["Date", "stadium_name", "temp_C", "rel_humidity", "wind_kph"]):
            weather_df = weather_df.rename({
                "Date": "date",
                "temp_C": "temp",
                "rel_humidity": "humidity",
                "wind_kph": "wind"
            })
            weather_subset = weather_df.select(["date", "stadium_name", "temp", "humidity", "wind"]).unique(subset=["date", "stadium_name"])
            df = df.join(weather_subset, on=["date", "stadium_name"], how="left")
        else:
            df = df.with_columns([
                pl.lit(None).alias("temp"),
                pl.lit(None).alias("humidity"),
                pl.lit(None).alias("wind"),
            ])
    else:
        df = df.with_columns([
            pl.lit(None).alias("temp"),
            pl.lit(None).alias("humidity"),
            pl.lit(None).alias("wind"),
        ])

    # Year and Week are already numeric now

    # Create bidirectional records
    cols_to_select = [
        pl.col("year"),
        pl.col("week"),
        pl.col("stadium_name"),
        pl.col("indoor_outdoor") if "indoor_outdoor" in df.columns else pl.lit(None).alias("indoor_outdoor"),
        pl.col("surface_type") if "surface_type" in df.columns else pl.lit(None).alias("surface_type"),
        pl.col("elevation").cast(pl.Float64, strict=False) if "elevation" in df.columns else pl.lit(None).cast(pl.Float64).alias("elevation"),
        pl.col("temp").cast(pl.Float64, strict=False) if "temp" in df.columns else pl.lit(None).cast(pl.Float64).alias("temp"),
        pl.col("humidity").cast(pl.Float64, strict=False) if "humidity" in df.columns else pl.lit(None).cast(pl.Float64).alias("humidity"),
        pl.col("wind").cast(pl.Float64, strict=False) if "wind" in df.columns else pl.lit(None).cast(pl.Float64).alias("wind"),
        pl.col("city") if "city" in df.columns else pl.lit(None).alias("city"),
        pl.col("state") if "state" in df.columns else pl.lit(None).alias("state"),
        pl.col("home_team") if "home_team" in df.columns else pl.lit(None).alias("home_team"),
    ]

    winners = df.select(cols_to_select + [
        pl.col("winner").alias("team"),
        pl.col("loser").alias("opponent"),
        pl.lit("Winner").alias("game_result")
    ])

    losers = df.select(cols_to_select + [
        pl.col("loser").alias("team"),
        pl.col("winner").alias("opponent"),
        pl.lit("Loser").alias("game_result")
    ])

    rich_schedule = pl.concat([winners, losers])
    
    # Normalize team names for joining
    rich_schedule = rich_schedule.with_columns([
        pl.col("team").map_elements(get_team_slug, return_dtype=pl.String),
        pl.col("opponent").map_elements(get_team_slug, return_dtype=pl.String),
        pl.col("home_team").map_elements(get_team_slug, return_dtype=pl.String).alias("home_team_slug"),
    ]).with_columns(
        pl.when(pl.col("home_team_slug").is_null())
        .then(None)
        .when(pl.col("team") == pl.col("home_team_slug"))
        .then(pl.lit("Home"))
        .otherwise(pl.lit("Away"))
        .alias("home_away")
    ).drop("home_team_slug", "home_team")
    
    return rich_schedule.unique(subset=["year", "week", "team"])

def enrich_weekly_stats(df: pl.DataFrame) -> pl.DataFrame:
    """
    Enrich player stats with high-fidelity matchup and environmental metadata.
    """
    if df.is_empty():
        return df

    # 1. Fetch rich schedule info
    schedule = get_rich_schedule()

    # 2. Clean old metadata columns to avoid duplicates
    if not schedule.is_empty():
        # Identify non-join columns in the schedule that might exist in the stats DF
        overlap_cols = set(schedule.columns) - {"year", "week", "team"}
        to_drop = [c for c in overlap_cols if c in df.columns]
        if to_drop:
            df = df.drop(to_drop)

    # 3. Normalize player team name
    if "team" in df.columns:
        df = df.with_columns(pl.col("team").map_elements(get_team_slug, return_dtype=pl.String))
    
    # 4. Join rich schedule info
    if not schedule.is_empty():
        # Ensure join keys have matching types
        df = df.with_columns([
            pl.col("year").cast(pl.Int64),
            pl.col("week").cast(pl.Int64)
        ])
        df = df.join(schedule, on=["year", "week", "team"], how="left")
    
    # 3. Add season label
    if "year" in df.columns:
        df = df.with_columns(
            pl.col("year").map_elements(normalize_season, return_dtype=pl.String).alias("season")
        )
    
    return df
