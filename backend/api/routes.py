from fastapi import APIRouter, HTTPException
from services.qb_service import get_qb_top_rankings
from services.rb_service import get_rb_top_rankings
from services.wr_service import get_wr_top_rankings
from services.te_service import get_te_top_rankings
from services.k_service import get_k_top_rankings

router = APIRouter()

@router.get("/{position}s/stats")
def stats_by_position(position: str):
    pos = position.lower()
    if pos == "qb":
        return get_qb_top_rankings()
    elif pos == "rb":
        return get_rb_top_rankings()
    elif pos == "wr":
        return get_wr_top_rankings()
    elif pos == "te":
        return get_te_top_rankings()
    elif pos == "k":
        return get_k_top_rankings()
    else:
        raise HTTPException(status_code=404, detail="Position not found")
