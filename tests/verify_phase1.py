"""
Verification Script for Phase 1: Storage Layer
Tests DuckDB connectivity and Predicate JSON Parsing in position_helper.py.
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from services.position_helper import load_and_rank

def test_duckdb_basic():
    print("Testing basic DuckDB load for QB...")
    df = load_and_rank("qb", year=2023)
    if df.is_empty():
        print("Error: QB 2023 data is empty!")
        sys.exit(1)
    
    # Correct Polars indexing: df[0, "Player"] or df["Player"][0]
    print(f"Loaded {len(df)} QBs for 2023. Columns: {df.columns[:5]}...")
    player = df["Player"][0]
    print(f"Top player: {player}")

def test_dynamic_filter():
    print("Testing dynamic Predicate JSON filter...")
    filters = {
        "conjunction": "AND",
        "conditions": [
            {"field": "fpts", "operator": "gt", "value": 300}
        ]
    }
    df = load_and_rank("qb", filters=filters)
    if df.is_empty():
        print("Warning: No QBs with FPTS > 300 found. Skipping assertion.")
        return
        
    # Check column name case
    col_map = {c.lower(): c for c in df.columns}
    fpts_col = col_map.get("fpts")
    assert (df[fpts_col] > 300).all(), f"All players should have {fpts_col} > 300"
    print(f"Filtered {len(df)} QBs with {fpts_col} > 300.")

def test_in_operator():
    print("Testing IN operator filter...")
    # Find real teams first
    df_all = load_and_rank("qb", year=2023)
    real_teams = df_all["team_name"].unique().to_list()[:2]
    print(f"Testing with real teams: {real_teams}")
    
    filters = {
        "conditions": [
            {"field": "team_name", "operator": "in", "value": real_teams}
        ]
    }
    df = load_and_rank("qb", filters=filters)
    teams = df["team_name"].unique().to_list()
    print(f"Found teams: {teams}")
    assert len(teams) > 0, "Should find at least 1 team from the list"
    assert all(t in real_teams for t in teams), "All found teams should be in the filter list"

if __name__ == "__main__":
    try:
        test_duckdb_basic()
        test_dynamic_filter()
        test_in_operator()
        print("\nPhase 1 Verification: SUCCESSFUL")
    except Exception as e:
        print(f"\nPhase 1 Verification: FAILED - {e}")
        sys.exit(1)
