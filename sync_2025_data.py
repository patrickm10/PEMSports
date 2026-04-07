import duckdb
import pandas as pd
from pathlib import Path

# Paths
DB_PATH = "data/nfl_stats.db"
RAW_DIR = "data_local/raw_scrapes"
V3_DIR = "data/v3"

def sync_position(position: str, raw_filename: str, target_year: int = 2025):
    print(f"--- Synchronizing {position.upper()} ({target_year}) ---")
    con = duckdb.connect(DB_PATH)
    
    # 1. Get the schema and metadata mapping
    # We borrow metadata from 2024 records to enrich new records (as requested)
    table_name = f"{position.lower()}_stats"
    cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
    metadata_cols = ['Team Name', 'stadium_name', 'city', 'state', 'latitude', 'longitude']
    
    # Create player -> metadata map from 2024
    metadata_map = con.execute(f"""
        SELECT DISTINCT Player, {', '.join([f'"{c}"' for c in metadata_cols])}
        FROM {table_name} 
        WHERE year = 2024
    """).df().drop_duplicates(subset=['Player']).set_index('Player').to_dict('index')
    
    # 2. Load 2025 Raw Data
    raw_path = Path(RAW_DIR) / raw_filename
    if not raw_path.exists():
        print(f"Skipping {position}: Raw file {raw_filename} not found.")
        return
        
    df_2025 = pd.read_csv(raw_path)
    df_2025['year'] = target_year
    
    # 3. Column Mapping (Normalization)
    # This aligns the scraped 'ATT/YDS' with the official DuckDB schema
    mapping = {
        'ATT': 'Pass_Att',
        'YDS': 'Pass_Yds',
        'TD': 'Pass_TD',
        'INT': 'Pass_Int',
        'SACKS': 'Sacks',
        'R_ATT': 'Rush_Att',
        'R_YDS': 'Rush_Yds',
        'R_TD': 'Rush_TD',
    }
    df_2025 = df_2025.rename(columns=mapping)
    
    # 4. Enrich with 2024 Metadata
    for col in metadata_cols:
        df_2025[col] = df_2025['Player'].apply(lambda x: metadata_map.get(x, {}).get(col, None))
        
    # 5. Schema Padding (Ensure all DB columns exist)
    numeric_cols = ['FPTS', 'FPTS/G', 'Pass_Att', 'Pass_Yds', 'Pass_TD', 'Pass_Int', 'Rush_Att', 'Rush_Yds', 'Rush_TD', 'Sacks', 'fpts_ppr']
    for col in cols:
        if col not in df_2025.columns:
            # Check for Case-Insensitive matches if rename missed it
            lower_map = {c.lower(): c for c in df_2025.columns}
            if col.lower() in lower_map:
                df_2025[col] = df_2025[lower_map[col.lower()]]
            else:
                df_2025[col] = 0 if col in numeric_cols else None
        else:
            # Fill existing nulls in numeric columns
            if col in numeric_cols:
                df_2025[col] = df_2025[col].fillna(0)
    
    # Final column order to match DB
    df_2025 = df_2025[cols]
    
    # 6. Append to DuckDB
    # Deduplicate: Check if records already exist for this year and position
    existing_count = con.execute(f"SELECT count(*) FROM {table_name} WHERE year = {target_year}").fetchone()[0]
    if existing_count > 0:
        print(f"Removing {existing_count} existing {target_year} records for {position}...")
        con.execute(f"DELETE FROM {table_name} WHERE year = {target_year}")
        
    print(f"Ingesting {len(df_2025)} new records for {target_year}...")
    con.register(f'temp_sync_{target_year}', df_2025)
    con.execute(f"INSERT INTO {table_name} SELECT * FROM temp_sync_{target_year}")
    
    # 7. Sync V3 Parquet (For High-Performance Context)
    parquet_path = Path(V3_DIR) / f"{position.lower()}_stats.parquet"
    print(f"Updating V3 Parquet layer: {parquet_path}")
    con.execute(f"COPY {table_name} TO '{parquet_path}' (FORMAT PARQUET)")
    
    con.close()
    print(f"SUCCESS: {position.upper()} synchronized.\n")

if __name__ == "__main__":
    sync_positions = [
        ("qb", "official_qb_2025_weeks.csv"),
        ("rb", "official_rb_2025_weeks.csv"),
        ("wr", "official_wr_2025_weeks.csv"),
        ("te", "official_te_2025_weeks.csv"),
        ("k", "official_k_2025_weeks.csv"),
    ]
    
    # Target year configuration
    # Change this to 2026 after running your 2026 data ingestion pipelines
    CURRENT_SYNC_YEAR = 2025

    for pos, filename in sync_positions:
        try:
            sync_position(pos, filename, target_year=CURRENT_SYNC_YEAR)
        except Exception as e:
            print(f"FAILED {pos}: {e}")
