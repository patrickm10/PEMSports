import polars as pl
from pathlib import Path

def analyze_position(pos):
    data_dir = Path("data/official_rankings/position")
    p_path = data_dir / f"{pos}_historical.parquet"
    if not p_path.exists():
        print(f"{pos}: No Parquet file found.")
        return

    df = pl.read_parquet(p_path)
    print(f"--- Analysis for {pos} ---")
    print(f"Total rows: {len(df)}")
    
    # Check for duplicates on (year, player_id)
    is_dupe = df.is_duplicated() if not hasattr(df, 'is_duplicated') else df.select(pl.all()).is_duplicated()
    # Simpler:
    dupes = df.filter(df.is_duplicated())
    # Actually, let's just use unique and compare counts
    unique_count = len(df.unique(subset=['year', 'player_id']))
    print(f"Unique rows (year, player_id): {unique_count}")
    print(f"Duplicate rows count: {len(df) - unique_count}")
    
    print("Sample rows (top 3):")
    print(df.select(['year', 'player_name', 'team', 'position', 'fpts_ppr']).head(3))
    
    # Check if position column matches expected
    actual_positions = df['position'].unique().to_list()
    print(f"Actual positions found in file: {actual_positions}")
    
    print(f"Distinct years: {df['year'].unique().sort(descending=True).to_list()}")
    print("\n")

if __name__ == "__main__":
    analyze_position("WR")
    analyze_position("K")
