"""Schema dump: Verify exact column names and 2025 row counts in DuckDB."""
import duckdb

DB_PATH = "data/nfl_stats.db"
POSITIONS = ["qb", "rb", "wr", "te", "k"]

con = duckdb.connect(DB_PATH, read_only=True)
for pos in POSITIONS:
    table = f"{pos}_stats"
    cols = con.execute(f"PRAGMA table_info({table})").fetchall()
    print(f"\n=== {table} ===")
    for col in cols:
        print(f"  {col[1]:25s} {col[2]}")
    
    count = con.execute(f"SELECT count(*) FROM {table} WHERE year = 2025").fetchone()[0]
    distinct_players = con.execute(f"SELECT count(DISTINCT Player) FROM {table} WHERE year = 2025").fetchone()[0]
    print(f"  --- 2025 rows: {count}, distinct players: {distinct_players}")

con.close()
