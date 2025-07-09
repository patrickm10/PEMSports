# services/rb_service.py
from .position_helper import load_and_rank, reorder_columns

POSITION = "rb"

EXTRA_STATS = [
    "Score", "FPTS",          # scoring fields
    "ATT", "Rush YDS", "Y/A", "LG", "20+", "Rush TD",
    "REC", "TGT", "Rec Yds", "Y/R", "Rec TD", "FL",
    "stadium_name", "indoor_outdoor", "surface_type",
    "elevation", "year_opened", "city", "state", "latitude", "longitude",
]

def get_rb_top_rankings(year: int | None = None, week: int | None = None):
    try:
        df = load_and_rank(POSITION, year=year, week=week)
        df = reorder_columns(df, EXTRA_STATS)
        return df.to_dicts()
    except Exception as exc:
        return {"error": str(exc)}
