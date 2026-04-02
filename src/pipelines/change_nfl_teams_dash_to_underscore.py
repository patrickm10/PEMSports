import polars as pl


roster_df = pl.read_csv("backend/static/data/nfl_metadata/nfl_rosters_2018_2025.csv")

roster_df = roster_df.with_columns(
	pl.col("Team").str.replace("-", "_").alias("Team")
)

roster_df.write_csv("backend/static/data/nfl_metadata/nfl_rosters_2018_2025.csv")
