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
STADIUM_CSV_PATH = BASE_DATA_DIR / "stadium.csv"


def build_home_stadium_map() -> pl.DataFrame:
    """
    Map canonical team slug → home stadium_name from stadium.csv.

    Used when nfl_matchups_enriched.csv is absent (CI/Render builds that only
    commit rankings parquet + stadium metadata).
    """
    if not STADIUM_CSV_PATH.exists():
        return pl.DataFrame(schema={"team": pl.Utf8, "stadium_name": pl.Utf8})

    df = pl.read_csv(STADIUM_CSV_PATH)
    if "team_name" not in df.columns or "stadium_name" not in df.columns:
        return pl.DataFrame(schema={"team": pl.Utf8, "stadium_name": pl.Utf8})

    return df.select(
        [
            pl.col("team_name").map_elements(get_team_slug, return_dtype=pl.String).alias("team"),
            pl.col("stadium_name"),
        ]
    ).unique(subset=["team"])


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


def build_home_away_from_stadium(
    weekly: pl.DataFrame,
    *,
    stadium_map: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """
    Derive (year, week, team) → home_away by comparing game stadium to home stadium.

    Fallback when enriched matchups are unavailable. Requires `stadium_name` on weekly rows.
    """
    required = {"year", "week", "team", "stadium_name"}
    if weekly.is_empty() or not required.issubset(set(weekly.columns)):
        return pl.DataFrame(
            schema={
                "year": pl.Int64,
                "week": pl.Int64,
                "team": pl.Utf8,
                "home_away": pl.Utf8,
            }
        )

    mapping = stadium_map if stadium_map is not None else build_home_stadium_map()
    if mapping.is_empty():
        return pl.DataFrame(
            schema={
                "year": pl.Int64,
                "week": pl.Int64,
                "team": pl.Utf8,
                "home_away": pl.Utf8,
            }
        )

    home_stadiums = mapping.rename({"stadium_name": "home_stadium_name"})

    keys = weekly.select(
        [
            pl.col("year").cast(pl.Int64, strict=False),
            pl.col("week").cast(pl.Int64, strict=False),
            pl.col("team"),
            pl.col("stadium_name"),
        ]
    ).unique(subset=["year", "week", "team"])

    joined = keys.join(home_stadiums, on="team", how="left")
    return joined.with_columns(
        pl.when(pl.col("stadium_name").is_null() | pl.col("home_stadium_name").is_null())
        .then(None)
        .when(
            pl.col("stadium_name").str.strip_chars().str.to_lowercase()
            == pl.col("home_stadium_name").str.strip_chars().str.to_lowercase()
        )
        .then(pl.lit("Home"))
        .otherwise(pl.lit("Away"))
        .alias("home_away")
    ).select(["year", "week", "team", "home_away"])
