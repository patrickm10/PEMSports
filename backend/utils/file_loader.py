from pathlib import Path
import polars as pl

def load_csv_data(filename: str) -> pl.DataFrame:
    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "frontend" / "nflstats-frontend" / "public" / "data" / "official_stats" / filename
    return pl.read_csv(csv_path)
