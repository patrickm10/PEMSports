import streamlit as st
import duckdb
import pandas as pd

DATA_PATH = "historical/qb_2020_2025_historical.csv"

@st.cache_resource
def setup_duckdb_connection(csv_path: str):
    con = duckdb.connect()
    con.execute(f"""
        CREATE OR REPLACE VIEW qb_data AS
        SELECT 
            *,
            TRIM(Player) AS player_key,
            CAST(CMP AS DOUBLE),
            CAST(ATT AS DOUBLE),
            CAST(TD AS DOUBLE),
            CAST(INT AS DOUBLE),
            CAST(YDS AS DOUBLE),
            CAST(FPTS AS DOUBLE),
            CAST(elevation AS DOUBLE)
        FROM read_csv_auto('{csv_path}', header=True, ignore_errors=True)
    """)
    return con

def run_query(con, sql: str) -> pd.DataFrame:
    return con.execute(sql).fetchdf()

st.set_page_config(page_title="QB Fantasy Analysis", layout="wide")
st.title("Quarterback Fantasy Stats (2020–2025)")


# Connect
try:
    con = setup_duckdb_connection(DATA_PATH)
    st.write(run_query(con, "SELECT * FROM qb_data LIMIT 1"))
except Exception as e:
    st.error(f"Error loading file: {e}")
    st.stop()

# Analysis options
analysis_queries = {
    "Best QBs vs Each Team (min 3 games)": """
        SELECT 
            player_key, 
            away_team_name AS opponent_team,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            ROUND(AVG(TD), 2) AS avg_touchdowns,
            ROUND(AVG(YDS), 2) AS avg_yards,
            COUNT(*) AS games
        FROM qb_data
        WHERE away_team_name != home_team_name
        GROUP BY player_key, away_team_name
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 50
    """,

    "Indoor vs Outdoor Performance (min 3 games)": """
        SELECT 
            player_key,
            indoor_outdoor,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM qb_data
        WHERE indoor_outdoor IS NOT NULL
        GROUP BY player_key, indoor_outdoor
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """,

    "Surface Type Impact (min 3 games)": """
        SELECT 
            player_key,
            surface_type,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM qb_data
        WHERE surface_type IN ('Grass', 'Turf')
        GROUP BY player_key, surface_type
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """,

    "Elevation Impact (min 3 games)": """
        SELECT 
            player_key,
            CASE 
                WHEN elevation >= 500 THEN 'High'
                WHEN elevation BETWEEN 100 AND 499 THEN 'Medium'
                ELSE 'Low'
            END AS elevation_level,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games
        FROM qb_data
        GROUP BY player_key, elevation_level
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 20
    """,

    "Defense Weakness (Avg Points Allowed)": """
        SELECT 
            home_team_name AS defense_team,
            ROUND(AVG(FPTS), 2) AS avg_points_allowed,
            COUNT(*) AS games
        FROM qb_data
        GROUP BY home_team_name
        ORDER BY avg_points_allowed DESC
        LIMIT 20
    """,

    "Optimal Conditions Summary": """
        SELECT 
            player_key,
            indoor_outdoor,
            surface_type,
            CASE 
                WHEN elevation >= 500 THEN 'High'
                WHEN elevation BETWEEN 100 AND 499 THEN 'Medium'
                ELSE 'Low'
            END AS elevation_level,
            home_team_name AS opponent_defense,
            ROUND(AVG(FPTS), 2) AS avg_fantasy_points,
            COUNT(*) AS games_played
        FROM qb_data
        WHERE
        FPTS IS NOT NULL AND
        home_team_name IS NOT NULL AND
        home_team_name != Team
        GROUP BY 
            player_key, indoor_outdoor, surface_type, elevation_level, home_team_name
        HAVING COUNT(*) >= 3
        ORDER BY avg_fantasy_points DESC
        LIMIT 200
    """
}

selected_analysis = st.sidebar.selectbox("Choose an analysis", list(analysis_queries.keys()))
df = run_query(con, analysis_queries[selected_analysis])

# Filters for Optimal Conditions
if selected_analysis == "Optimal Conditions Summary":
    st.markdown("### Optimal Conditions for QB Performance")

    elev_filter = st.sidebar.multiselect("Elevation Level", ["High", "Medium", "Low"])
    surface_filter = st.sidebar.multiselect("Surface Type", df["surface_type"].dropna().unique())
    indoor_filter = st.sidebar.multiselect("Indoor/Outdoor", df["indoor_outdoor"].dropna().unique())
    defense_filter = st.sidebar.multiselect("Opponent Defense", df["opponent_defense"].dropna().unique())

    # Apply filters
    if elev_filter:
        df = df[df["elevation_level"].isin(elev_filter)]
    if surface_filter:
        df = df[df["surface_type"].isin(surface_filter)]
    if indoor_filter:
        df = df[df["indoor_outdoor"].isin(indoor_filter)]
    if defense_filter:
        df = df[df["opponent_defense"].isin(defense_filter)]

    st.dataframe(df, use_container_width=True)

else:
    st.subheader(selected_analysis)
    st.dataframe(df, use_container_width=True)

    # Optional charts
    if "Elevation" in selected_analysis:
        st.bar_chart(df.set_index("player_key")["avg_fantasy_points"])
    elif "Defense Weakness" in selected_analysis:
        st.bar_chart(df.set_index("defense_team")["avg_points_allowed"])
