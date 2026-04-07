import polars as pl
import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Constants
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "nfl_stats.db"
CORE = ["Rank", "Player", "team_name"]
TRAILING = ["G", "ROST", "week", "year"]

from .query_builder import ASTCompiler

class PredicateParser:
    """
    Parses dynamic filter objects into DuckDB WHERE clauses.
    Supports complex nested logical predicates for the V3 Workspace via AST.
    """
    @staticmethod
    def parse(filter_obj: Optional[Dict[str, Any]], column_names: List[str]) -> Tuple[str, List[Any]]:
        if not filter_obj or "conditions" not in filter_obj:
            return "1=1", []
        
        # We now use the ASTCompiler to build the query safely
        ast = ASTCompiler.from_dict(filter_obj, column_names)
        return ASTCompiler.compile(ast)

def get_db_connection():
    """Ensure a fresh connection to the persistent DuckDB instance."""
    return duckdb.connect(str(DB_PATH))

def load_and_rank(
    position: str, 
    *, 
    year: Optional[int] = None, 
    week: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None
) -> pl.DataFrame:
    """
    Load positional data from DuckDB, apply dynamic filters, and assign Rank.
    Replaces the legacy CSV loader for V3 performance requirements.
    """
    table_name = f"{position.lower()}_stats"
    
    # Build the base WHERE clause with params
    where_parts = []
    params = []
    
    if year is not None:
        where_parts.append("year = ?")
        params.append(year)
    if week is not None:
        where_parts.append("week = ?")
        params.append(week)
    
    # Get column names for case-insensitive filter mapping
    with get_db_connection() as con:
        column_names = [c[1] for c in con.execute(f"PRAGMA table_info({table_name})").fetchall()]
    
    # Integrate dynamic V3 filters (Safe IR / Parameterized)
    if filters:
        sql_fragment, filter_params = PredicateParser.parse(filters, column_names)
        where_parts.append(f"({sql_fragment})")
        params.extend(filter_params)
        
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    # 2. Performance-First Query Decision
    # If week is None, we MUST aggregate to avoid displaying duplicate player rows
    if week is None:
        print(f"Applying Seasonal Aggregation for {position}...")
        query = f"""
            SELECT 
                ANY_VALUE(Rank) as orig_rank, -- Placeholder
                Player,
                year,
                SUM(CMP) as CMP,
                SUM(ATT) as ATT,
                CASE WHEN SUM(ATT) > 0 THEN (SUM(CMP)::FLOAT / SUM(ATT) * 100) ELSE 0 END as PCT,
                SUM(YDS) as YDS,
                CASE WHEN SUM(ATT) > 0 THEN (SUM(YDS)::FLOAT / SUM(ATT)) ELSE 0 END as "Y/A",
                SUM(TD) as TD,
                SUM(INT) as INT,
                SUM(SACKS) as SACKS,
                SUM(R_ATT) as R_ATT,
                SUM(R_YDS) as R_YDS,
                SUM(R_TD) as R_TD,
                SUM(FL) as FL,
                COUNT(*) as G,
                SUM(FPTS) as FPTS,
                (SUM(FPTS)::FLOAT / COUNT(*)) as "FPTS/G",
                ANY_VALUE(ROST) as ROST,
                AVG(Score) as Score,
                'Season' as week,
                ANY_VALUE("Team Name") as "Team Name",
                ANY_VALUE(stadium_name) as stadium_name,
                ANY_VALUE(city) as city,
                ANY_VALUE(state) as state,
                ANY_VALUE(latitude) as latitude,
                ANY_VALUE(longitude) as longitude
            FROM {table_name} 
            WHERE {where_clause}
            GROUP BY Player, year
        """
    else:
        query = f"SELECT * FROM {table_name} WHERE {where_clause}"
    
    # Execute high-performance parameterized query
    with get_db_connection() as con:
        df = con.execute(query, params).pl()

    if df.is_empty():
        return df

    # 3. Dynamic Re-Ranking (Based on Cumulative Performance)
    # Sort by FPTS descending to establish seasonal ranking
    df = df.sort("FPTS", descending=True)
    
    # Standardize Rank column (Resetting to 1-N)
    if "Rank" in df.columns:
        df = df.drop("Rank")
    if "orig_rank" in df.columns:
        df = df.drop("orig_rank")
        
    df = (
        df.with_row_index(name="Rank")
          .with_columns((pl.col("Rank") + 1).cast(pl.Int32))
    )
    return df

def reorder_columns(df: pl.DataFrame, extra_stats: List[str]) -> pl.DataFrame:
    """Keep CORE + extra stats, preserve others, push TRAILING to the end."""
    desired = CORE + extra_stats
    first = [c for c in desired if c in df.columns]
    middle = [c for c in df.columns if c not in first + TRAILING]
    last = [c for c in TRAILING if c in df.columns]
    return df.select(first + middle + last)
