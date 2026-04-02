import polars as pl

# helper to standardise club strings
def normalise(expr: pl.Expr) -> pl.Expr:
    return expr.str.to_lowercase().str.replace_all(" ", "_")

# legacy club names that need a current label
legacy = {
    "oakland_raiders":      "las_vegas_raiders",
    "washington_redskins":  "washington_commanders",
    "washington_football_team":  "washington_commanders",
}

# load files
games = pl.read_csv(
    "backend/static/data/nfl_metadata/new_total_nfl_matchups.csv",
    dtypes={"is_away": pl.Utf8},
)

stadiums = pl.read_csv("backend/static/data/nfl_metadata/nfl_stadiums.csv")

# tidy game log
games = (
    games
    .with_columns(
        [
            normalise(pl.col("Winner")).replace(legacy).alias("Winner"),
            normalise(pl.col("Loser")).replace(legacy).alias("Loser"),
            pl.col("is_away").fill_null("").alias("is_away"),
            pl.col("Date").str.strptime(pl.Date, "%Y-%m-%d").dt.year().alias("Year"),
        ]
    )
    .with_columns(
        pl.when(pl.col("is_away") == "@")
          .then(pl.col("Loser"))
          .otherwise(pl.col("Winner"))
          .alias("home_team_norm")
    )
)



# tidy stadium table
stadiums = stadiums.with_columns(
    normalise(pl.col("home_team_name")).replace(legacy).alias("home_team_norm")
)

# enrich game log
joined = games.join(
    stadiums,
    on="home_team_norm",
    how="left",
    suffix="_stadium",
).drop(["stadium_id"])

joined.write_csv("backend/static/data/nfl_metadata/nfl_matchups_enriched.csv")
print(f"Enriched file written to backend/static/data/nfl_metadata/nfl_matchups_enriched.csv")
