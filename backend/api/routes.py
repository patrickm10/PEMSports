from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
import base64
from backend.services.qb_service import get_qb_top_rankings
from backend.services.rb_service import get_rb_top_rankings
from backend.services.wr_service import get_wr_top_rankings
from backend.services.te_service import get_te_top_rankings
from backend.services.k_service import get_k_top_rankings

router = APIRouter()

@router.get("/{position}s/stats")
def stats_by_position(
    position: str,
    year: Optional[int] = Query(None),
    week: Optional[int] = Query(None),
    f: Optional[str] = Query(None, description="Base64 encoded filters")
):
    pos = position.lower()
    filters = None
    if f:
        try:
            # Decode V3 filters from Base64
            decoded = base64.b64decode(f).decode('utf-8')
            filters = json.loads(decoded).get("filters")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid filter encoding")

    # Map to services (We should consolidate this, but for now we follow the existing pattern)
    from backend.services.position_helper import load_and_rank, reorder_columns
    
    try:
        df = load_and_rank(pos, year=year, week=week, filters=filters)
        if df.is_empty():
            return []
        
        # We need the EXTRA_STATS for each position. 
        # For simplicity in this V3 consolidation, we'll return all columns and let the frontend decide.
        return df.to_dicts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
