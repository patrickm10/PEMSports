from utils.file_loader import load_csv_data
import polars as pl

TRAILING = ["G", "ROST", "week", "year"]
CORE = ["Rank", "Player", "team_name"]


def load_and_rank(position: str, *, year: int | None, week: int | None) -> pl.DataFrame:
    """Load a position CSV, filter by year and week, assign Rank, sort by FPTS or Score."""
    file = f"sorted_enriched_{position}_2020_2024_cleaned.csv"
    df = load_csv_data(file, subdir="data/official_rankings/clean")

    if year is not None:
        df = df.filter(pl.col("year") == year)
    if week is not None:
        df = df.filter(pl.col("week") == week)

    sort_col = "FPTS" if "FPTS" in df.columns else "Score"
    df = df.sort(sort_col, descending=True)

    if "Rank" in df.columns:
        df = df.drop("Rank")

    df = (
        df.with_row_index(name="Rank")
          .with_columns((pl.col("Rank") + 1).cast(pl.Int32))
    )
    return df


def reorder_columns(df: pl.DataFrame, extra_stats: list[str]) -> pl.DataFrame:
    """Keep CORE + extra stats, preserve any other cols, push TRAILING to the end."""
    desired = CORE + extra_stats
    first = [c for c in desired if c in df.columns]
    middle = [c for c in df.columns if c not in first + TRAILING]
    last = [c for c in TRAILING if c in df.columns]

    return df.select(first + middle + last)
