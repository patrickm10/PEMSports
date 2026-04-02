import duckdb
import polars as pl
from pathlib import Path

DATA_PATH = "data/official_rankings/historical/official_rb_2020_2025_historical_data.csv"

def setup_duckdb_connection(csv_path: str):
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE VIEW rb_data AS
        SELECT 
            *,
            LOWER(TRIM(Player)) AS player_key,
            TRIM(Player) AS Player_clean,
            CAST(ATT AS DOUBLE) AS ATT,
            CAST(YDS AS DOUBLE) AS RUSH_YARDS,
            CAST(TD AS DOUBLE) AS RUSH_TD,
            CAST(REC AS DOUBLE) AS REC,
            CAST(R_YDS AS DOUBLE) AS REC_YARDS,
            CAST(R_TD AS DOUBLE) AS REC_TD,
            CAST(FPTS AS DOUBLE) AS FPTS,
            CAST(elevation AS DOUBLE) AS elevation
        FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
    """)
    return con

def fetch_pl_df(con, query: str) -> pl.DataFrame:
    return pl.from_pandas(con.execute(query).fetchdf())

def best_rbs_vs_each_team(con):
    print("\n=== Best RBs vs Each Team (min 3 games, excluding own team) ===")
    query = """
        SELECT 
            player_key,
            away_team_name AS opponent_team,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            ROUND(AVG(ATT), 1) AS avg_rush_attempts,
            ROUND(AVG(RUSH_YARDS), 1) AS avg_rush_yards,
            ROUND(AVG(REC), 1) AS avg_receptions,
            ROUND(AVG(REC_YARDS), 1) AS avg_rec_yards,
            ROUND(AVG(RUSH_TD + REC_TD), 1) AS avg_total_tds,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM rb_data
        WHERE away_team_name != home_team_name
        GROUP BY player_key, away_team_name
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 50
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def indoor_vs_outdoor(con):
    print("\n=== Indoor vs Outdoor RB Performance (min 3 games) ===")
    query = """
        SELECT 
            player_key,
            indoor_outdoor,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM rb_data
        WHERE indoor_outdoor IS NOT NULL
        GROUP BY player_key, indoor_outdoor
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def surface_type_impact(con):
    print("\n=== Surface Type Impact on RBs (Grass vs Turf, min 3 games) ===")
    query = """
        SELECT 
            player_key,
            surface_type,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM rb_data
        WHERE surface_type IN ('Grass', 'Turf')
        GROUP BY player_key, surface_type
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def elevation_impact(con):
    print("\n=== RB Elevation Performance (min 3 games) ===")
    query = """
        SELECT 
            player_key,
            CASE 
                WHEN elevation >= 500 THEN 'High'
                WHEN elevation BETWEEN 100 AND 499 THEN 'Medium'
                ELSE 'Low'
            END AS elevation_level,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM rb_data
        GROUP BY player_key, elevation_level
        HAVING games_played >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """
    df = fetch_pl_df(con, query)
    print(df)
    return df

def defense_weakness_heatmap(con):
    print("\n=== Defense Weakness vs RBs (Avg FPTS Allowed) ===")
    query = """
        SELECT 
            home_team_name AS defense_team,
            ROUND(AVG(FPTS), 2) AS avg_points_allowed,
            COUNT(DISTINCT CAST(year AS VARCHAR) || '-' || CAST(week AS VARCHAR)) AS games_played
        FROM rb_data
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

    best_rbs_vs_each_team(con)
    indoor_vs_outdoor(con)
    surface_type_impact(con)
    elevation_impact(con)
    defense_weakness_heatmap(con)

    con.close()

if __name__ == "__main__":
    main()
