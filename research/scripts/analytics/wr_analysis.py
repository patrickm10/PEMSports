import duckdb
import polars as pl
from pathlib import Path

WR_DATA_PATH = "data/official_rankings/historical/official_wr_2020_2025_historical_data.csv"

def setup_duckdb_connection(csv_path: str):
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE VIEW wr_data AS
        SELECT 
            *,
            TRIM(Player) AS Player_clean,
            LOWER(TRIM(Player)) AS player_key,
            CAST(REC AS DOUBLE) AS REC,
            CAST(TGT AS DOUBLE) AS TGT,
            CAST(YDS AS DOUBLE) AS YDS,
            CAST(TD AS DOUBLE) AS TD,
            CAST(FPTS AS DOUBLE) AS FPTS,
            CAST(elevation AS DOUBLE) AS elevation
        FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
    """)
    return con

def fetch_pl_df(con, query: str) -> pl.DataFrame:
    return pl.from_pandas(con.execute(query).fetchdf())

def top_wr_vs_each_team(con):
    print("\n=== Best WRs vs Each Team (min 3 games, excluding own team) ===")
    query = """
        SELECT 
            player_key,
            away_team_name AS opponent_team,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            ROUND(AVG(REC), 2) AS avg_receptions,
            ROUND(AVG(YDS), 2) AS avg_receiving_yards,
            ROUND(AVG(TGT), 2) AS avg_targets,
            ROUND(AVG(TD), 2) AS avg_touchdowns,
            COUNT(*) AS games_played
        FROM wr_data
        WHERE away_team_name != home_team_name
        GROUP BY player_key, away_team_name
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 50
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def indoor_outdoor_split(con):
    print("\n=== Indoor vs Outdoor WR Performance (min 3 games) ===")
    query = """
        SELECT 
            player_key,
            indoor_outdoor,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM wr_data
        WHERE indoor_outdoor IS NOT NULL
        GROUP BY player_key, indoor_outdoor
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def surface_type_impact(con):
    print("\n=== WR Surface Type Impact (Grass vs Turf, min 3 games) ===")
    query = """
        SELECT 
            player_key,
            surface_type,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            ROUND(AVG(REC), 2) AS avg_receptions,
            ROUND(AVG(YDS), 2) AS avg_yards,
            COUNT(*) AS games
        FROM wr_data
        WHERE surface_type IN ('Grass', 'Turf')
        GROUP BY player_key, surface_type
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def elevation_impact(con):
    print("\n=== WR Elevation Performance (min 3 games) ===")
    query = """
        SELECT 
            player_key,
            CASE 
                WHEN elevation >= 500 THEN 'High'
                WHEN elevation BETWEEN 100 AND 499 THEN 'Medium'
                ELSE 'Low'
            END AS elevation_level,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM wr_data
        GROUP BY player_key, elevation_level
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def defense_heatmap(con):
    print("\n=== WR Fantasy Points Allowed by Defense ===")
    query = """
        SELECT 
            home_team_name AS defense_team,
            ROUND(AVG(FPTS), 2) AS avg_points_allowed,
            COUNT(*) AS games
        FROM wr_data
        GROUP BY home_team_name
        ORDER BY avg_points_allowed DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def main():
    if not Path(WR_DATA_PATH).exists():
        raise FileNotFoundError(f"CSV not found at {WR_DATA_PATH}")

    con = setup_duckdb_connection(WR_DATA_PATH)

    top_wr_vs_each_team(con)
    indoor_outdoor_split(con)
    surface_type_impact(con)
    elevation_impact(con)
    defense_heatmap(con)

    con.close()

if __name__ == "__main__":
    main()
