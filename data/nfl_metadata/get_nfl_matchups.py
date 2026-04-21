import polars as pl
import os

def main() -> None:
    # Target 2018-2025 as requested
    years = list(range(2018, 2026))
    all_dfs = []
    
    metadata_dir = "data/nfl_metadata"
    
    for year in years:
        file_path = os.path.join(metadata_dir, f"{year}.csv")
        if os.path.exists(file_path):
            print(f"Reading local cleaned data for {year}")
            # Use the standardized 13-column schema from Step 0
            df = pl.read_csv(file_path)
            df = df.with_columns(pl.lit(int(year)).alias("Year"))
            
            # Ensure 'Week' is integer for consistent concatenation
            df = df.with_columns(pl.col("Week").cast(pl.Int64))
            
            all_dfs.append(df)
        else:
            print(f"Skipping {year}: File not found at {file_path}")
    
    if not all_dfs:
        print("No local CSV data found.")
        return

    # Combine all years
    combined = pl.concat(all_dfs, how="diagonal")
    
    # Rename for consistency with enrichment pipeline
    if "Winner/tie" in combined.columns:
        combined = combined.rename({"Winner/tie": "Winner"})
    if "Loser/tie" in combined.columns:
        combined = combined.rename({"Loser/tie": "Loser"})

    # Load stadium info
    stadium_path = os.path.join(metadata_dir, "stadium.csv")
    if os.path.exists(stadium_path):
        stadiums = pl.read_csv(stadium_path)
        
        # Determine home team
        # Logic: If 'at' column == '@', the Loser was the home team.
        # Otherwise, the Winner was the home team.
        if "at" in combined.columns:
            combined = combined.with_columns(
                pl.when(pl.col("at") == "@")
                .then(pl.col("Loser"))
                .otherwise(pl.col("Winner"))
                .alias("home_team")
            )
        else:
            # Fallback if 'at' is missing (should not happen after Phase 0)
            combined = combined.with_columns(pl.col("Winner").alias("home_team"))

        # Join with stadium metadata
        combined = combined.join(stadiums, left_on="home_team", right_on="team_name", how="left")
        print("Joined with stadium metadata.")
    
    # Output the final enriched reference file
    output_path = os.path.join(metadata_dir, "nfl_matchups_enriched.csv")
    combined.write_csv(output_path)
    print(f"Saved {len(combined)} enriched matchups to {output_path}")

if __name__ == "__main__":
    main()