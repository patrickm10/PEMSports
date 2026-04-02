import polars as pl
from pathlib import Path


def reorder_nfl_columns(pos):
    """
    Takes in an unsorted dataframe and reorders the dataframe by moving
    the free agents to the bottom
    Args:
        pos: NFL Offensive Position

    Returns:
        df: sorted DataFrame
    """

    path = Path(
        f"backend/static/data/official_rankings/clean/sorted_enriched_{pos}_2020_2024_cleaned.csv"
    )
    # path = Path(
    #     f"backend/static/data/official_rankings/season_totals/{pos}_season_totals_2020_2024.csv"
    # )
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    df = pl.read_csv(path)

    df_sorted = df.with_columns(
        pl.col("team_name").str.to_lowercase().str.contains("free_agent").alias("is_free_agent"),
        pl.col("Score").round(2)
    )
    
    df_sorted = df_sorted.sort(
        by=["is_free_agent", "year", "week"], descending=[False, False, False]
    )
    df_sorted = df_sorted.drop("is_free_agent")

    df_sorted = df_sorted.with_columns(
        pl.col("team_name").str.replace_all("_", " ")
        .str.to_titlecase().alias("Team Name")
    )
    df_sorted.write_csv(path)

    print(f"Table Reordered for {path}.")
    return df_sorted


def main():
    # positions = ["qb", "rb", "wr", "te", "k"]
    positions = ["qb"]

    for pos in positions:
        reorder_nfl_columns(pos)


if __name__ == "__main__":
    main()
