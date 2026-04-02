"""
NFL Unified Matchup Pipeline
Author: Patrick Mejia

Joins enriched matchups with weather, offensive aggregates, and
defensive stats to produce a single analytical CSV.
"""

import logging
import os

import polars as pl

from pipelines.constants import OFFENSIVE_POSITIONS

logger = logging.getLogger(__name__)

# ── File paths ──────────────────────────────────────────────────────────
MATCHUPS_CSV = "backend/static/data/nfl_metadata/nfl_matchups_enriched.csv"
WEATHER_CSV = "backend/static/data/nfl_metadata/nfl_matchups_with_weather.csv"
OFF_RANKINGS_DIR = "data/official_rankings/position"
DST_CSV = "data/official_rankings/position/DST_historical.csv"
OUTPUT_CSV = "backend/static/data/nfl_metadata/nfl_unified_matchups.csv"


# ── Offensive aggregation ───────────────────────────────────────────────

def _load_offensive_aggregates() -> pl.DataFrame:
    """
    Read each positional CSV, sum FPTS_PPR per (Team, Year),
    then pivot so each position gets its own column.

    Returns DataFrame with columns:
        Team, Year, off_total_fpts, off_qb_fpts, off_rb_fpts, ...
    """
    position_frames: list[pl.DataFrame] = []

    for pos in OFFENSIVE_POSITIONS:
        path = f"{OFF_RANKINGS_DIR}/{pos}_historical.csv"
        if not os.path.exists(path):
            logger.warning("Missing offensive file: %s", path)
            continue

        df = pl.read_csv(path)
        if "Team" not in df.columns or "FPTS_PPR" not in df.columns:
            logger.warning("Skipping %s — missing Team or FPTS_PPR", path)
            continue

        # Cast FPTS_PPR to float (may be string from CSV)
        df = df.with_columns(pl.col("FPTS_PPR").cast(pl.Float64, strict=False))
        if "Year" in df.columns:
            df = df.with_columns(pl.col("Year").cast(pl.Int64, strict=False))

        agg = (
            df.group_by(["Team", "Year"])
            .agg(pl.col("FPTS_PPR").sum().alias(f"off_{pos.lower()}_fpts"))
        )
        position_frames.append(agg)

    if not position_frames:
        logger.warning("No offensive data loaded")
        return pl.DataFrame()

    # Join all positions on (Team, Year)
    result = position_frames[0]
    for frame in position_frames[1:]:
        result = result.join(frame, on=["Team", "Year"], how="full", coalesce=True)

    # Compute total
    fpts_cols = [c for c in result.columns if c.startswith("off_") and c.endswith("_fpts")]
    result = result.with_columns(
        pl.sum_horizontal(*[pl.col(c).fill_null(0.0) for c in fpts_cols]).alias("off_total_fpts")
    )

    logger.info("Offensive aggregates: %d team-year rows", len(result))
    return result


# ── Defensive loading ───────────────────────────────────────────────────

_DST_KEEP_COLS = ["SACK", "INT", "FR", "FF", "DEF TD", "FPTS"]


def _load_defensive_stats() -> pl.DataFrame:
    """
    Read DST_historical.csv, keep key columns, rename for clarity.

    Returns DataFrame with columns:
        Team, Year, def_sack, def_int, def_fr, def_ff, def_td, def_fpts
    """
    if not os.path.exists(DST_CSV):
        logger.warning("DST CSV not found: %s", DST_CSV)
        return pl.DataFrame()

    df = pl.read_csv(DST_CSV)

    # Keep only available columns from the expected set
    available = [c for c in _DST_KEEP_COLS if c in df.columns]
    select_cols = ["Team", "Year"] + available
    select_cols = [c for c in select_cols if c in df.columns]
    df = df.select(select_cols)

    # Cast numeric
    for c in available:
        df = df.with_columns(pl.col(c).cast(pl.Float64, strict=False))
    if "Year" in df.columns:
        df = df.with_columns(pl.col("Year").cast(pl.Int64, strict=False))

    # Rename to prefixed names
    rename_map = {
        "SACK": "def_sack",
        "INT": "def_int",
        "FR": "def_fr",
        "FF": "def_ff",
        "DEF TD": "def_td",
        "FPTS": "def_fpts",
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename({old: new})

    logger.info("Defensive stats: %d team-year rows", len(df))
    return df


# ── Main join logic ─────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # 1. Load matchups
    matchups = pl.read_csv(MATCHUPS_CSV)
    matchups = matchups.with_columns(pl.col("Year").cast(pl.Int64, strict=False))
    logger.info("Matchups loaded: %d rows", len(matchups))

    # 2. Load weather and join via (Date, city)
    if os.path.exists(WEATHER_CSV):
        weather = pl.read_csv(WEATHER_CSV)
        wx_cols = ["Date", "city", "temp_C", "precip_mm", "wind_kph",
                    "rel_humidity", "pressure_hpa"]
        wx_cols = [c for c in wx_cols if c in weather.columns]
        weather = weather.select(wx_cols).unique(subset=["Date", "city"])

        matchups = matchups.join(weather, on=["Date", "city"], how="left")
        logger.info("Weather joined")
    else:
        logger.warning("Weather CSV not found — skipping weather join")

    # 3. Load offensive aggregates and join for Winner / Loser
    offense = _load_offensive_aggregates()
    if not offense.is_empty():
        offense = offense.with_columns(pl.col("Year").cast(pl.Int64, strict=False))
        off_cols = [c for c in offense.columns if c not in ("Team", "Year")]

        # Winner offense
        winner_off = offense.rename(
            {**{c: f"winner_{c}" for c in off_cols},
             "Team": "_join_team", "Year": "_join_year"}
        )
        matchups = matchups.join(
            winner_off,
            left_on=["Winner", "Year"],
            right_on=["_join_team", "_join_year"],
            how="left",
        )

        # Loser offense
        loser_off = offense.rename(
            {**{c: f"loser_{c}" for c in off_cols},
             "Team": "_join_team", "Year": "_join_year"}
        )
        matchups = matchups.join(
            loser_off,
            left_on=["Loser", "Year"],
            right_on=["_join_team", "_join_year"],
            how="left",
        )
        logger.info("Offensive stats joined")

    # 4. Load defensive stats and join for Winner / Loser
    defense = _load_defensive_stats()
    if not defense.is_empty():
        defense = defense.with_columns(pl.col("Year").cast(pl.Int64, strict=False))
        def_cols = [c for c in defense.columns if c not in ("Team", "Year")]

        # Winner defense
        winner_def = defense.rename(
            {**{c: f"winner_{c}" for c in def_cols},
             "Team": "_join_team", "Year": "_join_year"}
        )
        matchups = matchups.join(
            winner_def,
            left_on=["Winner", "Year"],
            right_on=["_join_team", "_join_year"],
            how="left",
        )

        # Loser defense
        loser_def = defense.rename(
            {**{c: f"loser_{c}" for c in def_cols},
             "Team": "_join_team", "Year": "_join_year"}
        )
        matchups = matchups.join(
            loser_def,
            left_on=["Loser", "Year"],
            right_on=["_join_team", "_join_year"],
            how="left",
        )
        logger.info("Defensive stats joined")

    # 5. Write output
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    matchups.write_csv(OUTPUT_CSV)
    logger.info(
        "Unified matchups written: %d rows, %d columns -> %s",
        len(matchups), len(matchups.columns), OUTPUT_CSV,
    )
    print(f"\n[OK] Final CSV: {OUTPUT_CSV}")
    print(f"  Rows: {len(matchups)}  |  Columns: {len(matchups.columns)}")
    print(f"  Columns: {matchups.columns}")


if __name__ == "__main__":
    main()
