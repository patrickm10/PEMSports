"""
Player stat transforms — cleaning, team extraction, column reordering.
Operates on Polars DataFrames produced by scrapers.
"""

import logging
import re
from typing import Optional

import polars as pl

from pipelines.constants import TEAM_MAP

logger = logging.getLogger(__name__)


import hashlib

def generate_player_id(name: str, position: str, team: str) -> str:
    """Generate deterministic MD5 hash for player identifier."""
    raw = f"{str(name).lower()}_{str(position).lower()}_{str(team).lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def clean_player_name(name: str) -> str:
    """
    Strip parenthetical team abbreviation from a player name.

    "Josh Allen (BUF)" → "Josh Allen"
    """
    if not isinstance(name, str):
        logger.warning("Expected str for player name, got %s: %s", type(name), name)
        return name
    return re.sub(r"\s*\(.*?\)", "", name).strip()


def clean_player_data(df: pl.DataFrame, position: str, year: int) -> pl.DataFrame:
    """
    Apply standard cleaning to a scraped positional DataFrame:

    1. Cast 'G' (games_played) to int and filter out players with 0 games.
    2. Add 'team' column derived from the player name field.
    3. Clean the 'player_name' field (remove team abbr).
    4. Generate deterministic 'player_id'.
    5. Ensure all columns are standard, lowercase pythonical names.
    """
    if df.is_empty():
        return df

    # Identify player name column (site uses 'PLAYER' or 'Player')
    name_col = "PLAYER" if "PLAYER" in df.columns else "Player"

    # Filter by games played
    if "G" in df.columns:
        df = (
            df.with_columns(pl.col("G").cast(pl.Int64, strict=False))
              .filter(pl.col("G") > 0)
        )

    from pipelines.transforms.team_stats import extract_dst_team_abbr

    # Add Team, then clean Player name
    df = df.with_columns([
        pl.col(name_col)
          .map_elements(extract_dst_team_abbr, return_dtype=pl.Utf8)
          .alias("team"),
        pl.col(name_col)
          .map_elements(clean_player_name, return_dtype=pl.Utf8)
          .alias("player_name"),
    ])

    # Downcase all existing columns
    df = df.rename({col: col.lower() for col in df.columns})

    # Rename standard feature columns
    rename_map = {}
    if "g" in df.columns:
        rename_map["g"] = "games_played"
    if name_col.lower() in df.columns and name_col.lower() != "player_name":
        # Drop the original duplicate name col if needed, or simply let the new one exist
        df = df.drop(name_col.lower())

    df = df.rename(rename_map)
    df = df.with_columns([
        pl.lit(position).alias("position"),
        pl.lit(year).cast(pl.Int64).alias("year")
    ])

    # Generate deterministic player_id natively using string concat directly in polars avoids py objects
    # But for safety/accuracy using map_elements
    df = df.with_columns(
        pl.struct(["player_name", "position", "team"])
        .map_elements(lambda r: generate_player_id(r["player_name"], r["position"], r["team"]), return_dtype=pl.Utf8)
        .alias("player_id")
    )
    
    return df
