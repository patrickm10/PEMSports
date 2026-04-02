import duckdb
import polars as pl
from pathlib import Path

# Constants
DATA_PATH = "backend/static/data/official_rankings/historical/qb_week_rankings_2018_2026.csv"
MIN_GAMES = 3

# Weather thresholds
RAIN_MM_LIGHT = 0.5
WIND_KPH_WINDY = 25.0
COLD_C = 5.0
FREEZING_C = 0.0

def setup_duckdb_connection(csv_path: str):
    """Initializes DuckDB with standardized views for QB analysis."""
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE VIEW qb_data AS
        SELECT
            TRIM(Player) AS Player,
            CAST(FPTS AS DOUBLE)          AS fpts,
            CAST("Pass_Yds" AS DOUBLE)    AS pass_yds,
            CAST("Pass_TD" AS DOUBLE)     AS pass_tds,
            CAST(temp_C AS DOUBLE)        AS temp_c,
            CAST(precip_mm AS DOUBLE)     AS precip_mm,
            CAST(wind_kph AS DOUBLE)      AS wind_kph,
            CAST(Year AS INTEGER)         AS year,
            COALESCE(indoor_outdoor, '')  AS condition,
            COALESCE(surface_type, '')    AS surface,
            CASE WHEN precip_mm >= {RAIN_MM_LIGHT} THEN 'Rain' ELSE 'No Rain' END AS rain_category,
            CASE WHEN wind_kph >= {WIND_KPH_WINDY} THEN 'Windy' ELSE 'Calm' END AS wind_category,
            CASE 
                WHEN temp_C <= {FREEZING_C} THEN 'Freezing'
                WHEN temp_C <= {COLD_C}    THEN 'Cold'
                WHEN temp_C <= 15          THEN 'Cool'
                WHEN temp_C <= 25          THEN 'Mild'
                ELSE 'Warm'
            END AS temp_band
        FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
    """)
    
    # Season-specific view
    con.execute("CREATE OR REPLACE VIEW qb_season AS SELECT * FROM qb_data WHERE year = (SELECT max(year) FROM qb_data)")
    return con

def run_query(con, title: str, sql: str):
    """
    Executes a SQL query, adds a rank, and prints a formatted top 5 table.
    Ensures consistency across all analytical outputs.
    """
    # Fetch result into Polars
    df = pl.from_pandas(con.execute(sql).fetchdf())
    
    if df.is_empty():
        print(f"\n--- {title} ---\nNo data available.")
        return

    # Standardize result: Rank and Top 5
    df = (
        df.with_columns(pl.lit(1).alias("Rank"))
        .with_columns(pl.col("Rank").cum_sum().alias("Rank"))
        .head(5)
    )

    # Reorder Rank to be first
    cols = ["Rank"] + [c for c in df.columns if c != "Rank"]
    df = df.select(cols)

    # Fetch Season Year for header
    year = con.execute("SELECT max(year) FROM qb_season").fetchone()[0]

    # Print Formatting
    print(f"\nSeason: {year}")
    print(f"\n{title}")
    print(df.to_init_repr()) # Using init repr for a clean table-like view or df.to_struct()...
    # Actually, plain print of Polars DF is quite clean, but let's make it slightly more custom
    print(df)

def main():
    if not Path(DATA_PATH).exists():
        print(f"Error: CSV not found at {DATA_PATH}")
        return

    con = setup_duckdb_connection(DATA_PATH)

    # Define analytical queries
    queries = {
        "Best QBs Overall": f"""
            SELECT 
                Player, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            GROUP BY Player
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """,
        "Indoor vs Outdoor": f"""
            SELECT 
                Player, 
                condition, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            WHERE condition IN ('Indoor', 'Outdoor')
            GROUP BY Player, condition
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """,
        "Surface Type Impact": f"""
            SELECT 
                Player, 
                surface, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            WHERE surface IN ('Grass', 'Turf')
            GROUP BY Player, surface
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """,
        "Rain Performance": f"""
            SELECT 
                Player, 
                rain_category, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            GROUP BY Player, rain_category
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """,
        "Wind Performance": f"""
            SELECT 
                Player, 
                wind_category, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            GROUP BY Player, wind_category
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """,
        "Temperature Band Performance": f"""
            SELECT 
                Player, 
                temp_band, 
                ROUND(AVG(fpts), 1) AS avg_fantasy_points, 
                COUNT(*) AS games
            FROM qb_season
            GROUP BY Player, temp_band
            HAVING count(*) >= {MIN_GAMES}
            ORDER BY avg_fantasy_points DESC
        """
    }

    # Execute and Display
    for title, sql in queries.items():
        run_query(con, title, sql)

    con.close()

if __name__ == "__main__":
    main()