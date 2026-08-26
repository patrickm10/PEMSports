"""
Schedule lookup helpers for home/away derivation.

Builds (year, week, team_slug) → home_away from nfl_matchups_enriched.csv.
Used by enrichment pipeline and bake_db post-processing.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from pipelines.enrichment import ENRICHED_MATCHUPS_PATH, get_team_slug

BASE_DATA_DIR = Path("data/nfl_metadata")


def build_home_away_schedule() -> pl.DataFrame:
    """
    Return schedule rows with team slug and home_away (Home | Away | null).

    One row per (year, week, team) for both winner and loser perspectives.
    """
    if not ENRICHED_MATCHUPS_PATH.exists():
        return pl.DataFrame(
            schema={
                "year": pl.Int64,
                "week": pl.Int64,
                "team": pl.Utf8,
                "home_away": pl.Utf8,
            }
        )

    df = pl.read_csv(ENRICHED_MATCHUPS_PATH, infer_schema_length=0)
    df = df.rename(
        {
            "Week": "week",
            "Year": "year",
            "Winner": "winner",
            "Loser": "loser",
        }
    )
    df = df.with_columns(
        [
            pl.col("year").cast(pl.Int64, strict=False),
            pl.col("week").cast(pl.Int64, strict=False),
        ]
    ).filter(pl.col("year").is_not_null() & pl.col("week").is_not_null())

    if "home_team" not in df.columns:
        return pl.DataFrame(
            schema={
                "year": pl.Int64,
                "week": pl.Int64,
                "team": pl.Utf8,
                "home_away": pl.Utf8,
            }
        )

    home_slug = pl.col("home_team").map_elements(get_team_slug, return_dtype=pl.String)

    winners = df.select(
        [
            pl.col("year"),
            pl.col("week"),
            pl.col("winner").map_elements(get_team_slug, return_dtype=pl.String).alias("team"),
            home_slug.alias("home_team_slug"),
        ]
    ).with_columns(
        pl.when(pl.col("team") == pl.col("home_team_slug"))
        .then(pl.lit("Home"))
        .when(pl.col("home_team_slug").is_not_null())
        .then(pl.lit("Away"))
        .otherwise(None)
        .alias("home_away")
    ).drop("home_team_slug")

    losers = df.select(
        [
            pl.col("year"),
            pl.col("week"),
            pl.col("loser").map_elements(get_team_slug, return_dtype=pl.String).alias("team"),
            home_slug.alias("home_team_slug"),
        ]
    ).with_columns(
        pl.when(pl.col("team") == pl.col("home_team_slug"))
        .then(pl.lit("Home"))
        .when(pl.col("home_team_slug").is_not_null())
        .then(pl.lit("Away"))
        .otherwise(None)
        .alias("home_away")
    ).drop("home_team_slug")

    schedule = pl.concat([winners, losers]).unique(subset=["year", "week", "team"])
    return schedule.select(["year", "week", "team", "home_away"])
