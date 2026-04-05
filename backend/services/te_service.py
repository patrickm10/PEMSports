from .position_helper import load_and_rank, reorder_columns
import polars as pl

POSITION = "te"

EXTRA_STATS = [
    "Score", "FPTS",
    "REC", "TGT", "Rec Yds", "Y/R", "LG", "20+", "Rec TD",
    "ATT", "Rush Yds", "Rush TD", "FL",
    "stadium_name", "indoor_outdoor", "surface_type",
    "elevation", "year_opened", "city", "state", "latitude", "longitude",
]

def get_te_top_rankings(year: int | None = None, week: int | None = None):
    try:
        df = load_and_rank(POSITION, year=year, week=week)
        df = reorder_columns(df, EXTRA_STATS)
        return df.to_dicts()
    except Exception as exc:
        return {"error": str(exc)}

def get_te_season_totals(year: int | None = None):
    try:
        path = "static/data/official_rankings/season_totals/te_season_totals_2020_2024.csv"
        df = pl.read_csv(path)

        if year is not None:
            df = df.filter(pl.col("year") == year)

        df = reorder_columns(df, EXTRA_STATS)
        return df.to_dicts()
    except Exception as exc:
        return {"error": str(exc)}
