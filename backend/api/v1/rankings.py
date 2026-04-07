from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import json
import base64
from backend.services.position_helper import load_and_rank, get_db_connection

router = APIRouter()

@router.get("/{position}")
def get_rankings(
    position: str,
    year: Optional[int] = Query(None),
    week: Optional[int] = Query(None),
    f: Optional[str] = Query(None, description="Base64 encoded filters")
):
    pos = position.lower()
    filters = None
    if f:
        try:
            decoded = base64.b64decode(f).decode('utf-8')
            filters = json.loads(decoded).get("filters")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid filter encoding")

    try:
        df = load_and_rank(pos, year=year, week=week, filters=filters)
        if df.is_empty():
            raise HTTPException(
                status_code=500,
                detail=f"CRITICAL: Zero data returned for position={pos}, year={year}, week={week}. "
                       f"This indicates a data-integrity failure in the Parquet/DuckDB layer."
            )

        # Zero-Transformation Passthrough: Polars dict → JSON response
        return df.to_dicts()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{position}/seasons")
def get_seasons(position: str):
    """Return a list of unique years available for a position."""
    pos = position.lower()
    table_name = f"{pos}_stats"
    try:
        with get_db_connection() as con:
            res = con.execute(f"SELECT DISTINCT year FROM {table_name} ORDER BY year DESC").fetchall()
            return [row[0] for row in res]
    except Exception as e:
        # Fallback to defaults if table doesn't exist
        return [2024, 2025]

@router.get("/{position}/weeks")
def get_weeks(position: str, year: int):
    """Return a list of unique weeks available for a position and year."""
    pos = position.lower()
    table_name = f"{pos}_stats"
    try:
        with get_db_connection() as con:
            res = con.execute(f"SELECT DISTINCT week FROM {table_name} WHERE year = ? ORDER BY week ASC", (year,)).fetchall()
            return [row[0] for row in res]
    except Exception as e:
        # Fallback to standard season weeks
        return list(range(1, 19))
