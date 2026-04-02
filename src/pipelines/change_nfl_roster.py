import polars as pl

def normalize(expr) -> pl.Expr:
    return expr.str.to_lowercase().str.replace_all("-", "_")

df = pl.read_csv("backend/static/data/nfl_metadata/nfl_rosters_2018_2025.csv")

df = df.with_columns(
    [
        normalize(pl.col("Team")).alias("Team")
    ]
)
print(df.filter(pl.col("Team") == "new_york_giants"))
df.write_csv("backend/static/data/nfl_metadata/nfl_rosters_2018_2025.csv")
