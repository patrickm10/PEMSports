import duckdb
import polars as pl
from pathlib import Path

DATA_PATH = "data/official_rankings/historical/official_k_2020_2025_historical_data.csv"

def setup_duckdb_connection(csv_path: str):
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE VIEW k_data AS
        SELECT 
            *,
            TRIM(Player) AS Player_clean,
            CAST(FG AS DOUBLE) AS FG,
            CAST(FGA AS DOUBLE) AS FGA,
            CAST(PCT AS DOUBLE) AS PCT,
            CAST(XPT AS DOUBLE) AS XPT,
            CAST(XPA AS DOUBLE) AS XPA,
            CAST(FPTS AS DOUBLE) AS FPTS,
            CAST(elevation AS DOUBLE) AS elevation
        FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
    """)
    return con

def fetch_pl_df(con, query: str) -> pl.DataFrame:
    return pl.from_pandas(con.execute(query).fetchdf())

def best_kickers_vs_each_team(con):
    print("\n=== Best Kickers vs Each Opponent (min 3 games, excluding own team) ===")
    query = """
        SELECT 
            Player,
            away_team_name AS opponent_team,
            ROUND(AVG(FG), 2) AS avg_field_goals_made,
            ROUND(AVG(FGA), 2) AS avg_field_goals_attempted,
            ROUND(AVG(PCT), 2) AS avg_fg_percentage,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM k_data
        WHERE away_team_name != home_team_name
        GROUP BY Player, away_team_name
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 30
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def indoor_vs_outdoor_kickers(con):
    print("\n=== Indoor vs Outdoor Kickers Performance (min 3 games) ===")
    query = """
        SELECT 
            Player,
            indoor_outdoor,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM k_data
        WHERE indoor_outdoor IS NOT NULL
        GROUP BY Player, indoor_outdoor
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def surface_type_impact_kickers(con):
    print("\n=== Surface Type Impact on Kickers (Grass vs Turf, min 3 games) ===")
    query = """
        SELECT 
            Player,
            surface_type,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM k_data
        WHERE surface_type IN ('Grass', 'Turf')
        GROUP BY Player, surface_type
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def elevation_impact_kickers(con):
    print("\n=== Kicker Elevation Performance (min 3 games) ===")
    query = """
        SELECT 
            Player,
            CASE 
                WHEN elevation >= 500 THEN 'High'
                WHEN elevation BETWEEN 100 AND 499 THEN 'Medium'
                ELSE 'Low'
            END AS elevation_level,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM k_data
        GROUP BY Player, elevation_level
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def defense_weakness_heatmap_kickers(con):
    print("\n=== Defense Weakness Heatmap vs Kickers (Avg FPTS Allowed) ===")
    query = """
        SELECT 
            home_team_name AS defense_team,
            ROUND(AVG(FPTS), 2) AS avg_points_allowed,
            COUNT(*) AS games
        FROM k_data
        GROUP BY home_team_name
        ORDER BY avg_points_allowed DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def main():
    if not Path(DATA_PATH).exists():
        raise FileNotFoundError(f"CSV not found at {DATA_PATH}")

    con = setup_duckdb_connection(DATA_PATH)

    best_kickers_vs_each_team(con)
    indoor_vs_outdoor_kickers(con)
    surface_type_impact_kickers(con)
    elevation_impact_kickers(con)
    defense_weakness_heatmap_kickers(con)

    con.close()

if __name__ == "__main__":
    main()
