import sys
import os
import duckdb
import pandas as pd

# Define paths
CSV_ROOT = "data_local/raw_scrapes"
DB_PATH = "data/nfl_stats.db"

def verify_player_stats(player_name, position="qb", year=2025):
    print(f"\nAUDITING: {player_name} ({year} {position.upper()})")
    
    # 1. Calculate Ground Truth from CSV
    csv_file = os.path.join(CSV_ROOT, f"official_{position.lower()}_{year}_weeks.csv")
    if not os.path.exists(csv_file):
        print(f"ERROR: Source file {csv_file} missing.")
        return False
        
    df_csv = pd.read_csv(csv_file)
    p_csv = df_csv[df_csv['Player'].str.contains(player_name, na=False)]
    
    csv_sum = p_csv['FPTS'].sum()
    csv_count = len(p_csv)
    
    # 2. Calculate Aggregated Stat from DuckDB
    con = duckdb.connect(DB_PATH)
    try:
        # We query the DB for the raw unaggregated week records first to check total ingestion
        db_raw = con.execute(f"""
            SELECT SUM(FPTS), COUNT(*) 
            FROM {position}_stats 
            WHERE Player LIKE '%{player_name}%' AND year = {year}
        """).fetchone()
        
        db_sum = db_raw[0] if db_raw[0] is not None else 0
        db_count = db_raw[1]
    finally:
        con.close()
        
    # 3. Validation
    print(f"Source CSV:   Sum={csv_sum:.2f}, Records={csv_count}")
    print(f"Target DB:    Sum={db_sum:.2f}, Records={db_count}")
    
    diff = abs(csv_sum - db_sum)
    if diff < 0.1 and csv_count == db_count:
        print("RESULT: PASS - Data integrity verified.")
        return True
    else:
        print(f"RESULT: FAIL - Discrepancy of {diff:.4f} detected.")
        return False

if __name__ == "__main__":
    players = [
        ("Josh Allen", "qb"),
        ("Baker Mayfield", "qb"),
        ("Lamar Jackson", "qb")
    ]
    
    results = []
    for name, pos in players:
        results.append(verify_player_stats(name, pos))
        
    if all(results):
        print("\n" + "="*40)
        print("GLOBAL STATUS: DATA INTEGRITY GREEN")
        print("="*40)
        sys.exit(0)
    else:
        print("\n" + "="*40)
        print("GLOBAL STATUS: DATA INTEGRITY RED")
        print("="*40)
        sys.exit(1)
