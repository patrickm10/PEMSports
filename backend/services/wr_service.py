from .position_helper import load_and_rank, reorder_columns

POSITION = "wr"

EXTRA_STATS = [
    "Score", "FPTS",
    "REC", "TGT", "Rec Yds", "Y/R", "LG", "20+", "Rec TD",
    "ATT", "Rush Yds", "Rush TD", "FL",
    "stadium_name", "indoor_outdoor", "surface_type",
    "elevation", "year_opened", "city", "state", "latitude", "longitude",
]

def get_wr_top_rankings(year: int | None = None, week: int | None = None):
    try:
        df = load_and_rank(POSITION, year=year, week=week)
        df = reorder_columns(df, EXTRA_STATS)
        return df.to_dicts()
    except Exception as exc:
        return {"error": str(exc)}
