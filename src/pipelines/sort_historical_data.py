import pandas as pd
from pathlib import Path

def sort_and_export_by_position(position: str):
    input_path = Path(f"backend/static/data/official_rankings/clean/sorted_enriched_{position}_2020_2024_cleaned.csv")
    output_path = Path(f"backend/static/data/official_rankings/clean/sorted_enriched_{position}_2020_2024_cleaned.csv")

    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist.")

    df = pd.read_csv(input_path)

    df["week"] = df["week"].astype(int)
    df["year"] = df["year"].astype(int)
    df["FPTS"] = pd.to_numeric(df["FPTS"], errors="coerce").fillna(0)

    # Optional: add position for clarity
    df["position"] = position

    # Mark free agents for sorting
    df["is_free_agent"] = df["team_name"].str.lower().str.contains("free_agent", na=False)

    # Sort by free agent flag, then year
    df_sorted = df.sort_values(by=["is_free_agent", "year", "FPTS"], ascending=[True, True, False])

    # Reset rank per year across all weeks for the position
    df_sorted["Rank"] = (
        df_sorted.groupby("year")["FPTS"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # Clean up
    df_sorted = df_sorted.drop(columns=["is_free_agent", "stadium_id", "FPTS/G", "team_abbr","position"], errors="ignore")
    df_sorted = df_sorted.sort_values(by=["year", "Rank"])
    df_sorted["Score"] = df_sorted["Score"].round(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_sorted.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")

def reorganize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Define the desired column order (adjust as needed)
    # Columns to move to the end
    move_last = ["G", "ROST", "week", "year"]
    # Columns to keep at the front (excluding those to move last)
    front = [col for col in df.columns if col not in move_last]
    # Only include columns that actually exist in the DataFrame
    move_last = [col for col in move_last if col in df.columns]
    new_order = [col for col in front if col not in move_last] + move_last
    df[new_order] = df[new_order].sort_values(by=["year", "week", "Rank"])
    return df[new_order]

# Run for all positions
for pos in ["qb", "rb", "wr", "te", "k"]:
    input_path = Path(f"backend/static/data/official_rankings/clean/sorted_enriched_{pos}_2020_2024_cleaned.csv")
    sort_and_export_by_position(pos)

    df = pd.read_csv(input_path)
    df = reorganize_columns(df)
    df.to_csv(input_path, index=False)
