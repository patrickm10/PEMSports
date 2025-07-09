from .position_helper import load_and_rank, reorder_columns

POSITION = "k"

EXTRA_STATS = [
    "Score", "FPTS",
    "FG", "FGA", "PCT", "LG",
    "1-19", "20-29", "30-39", "40-49", "50+",
    "XPT", "XPA",
    "stadium_name", "indoor_outdoor", "surface_type",
    "elevation", "year_opened", "city", "state", "latitude", "longitude",
]

def get_k_top_rankings(year: int | None = None, week: int | None = None):
    try:
        df = load_and_rank(POSITION, year=year, week=week)
        df = reorder_columns(df, EXTRA_STATS)
        return df.to_dicts()
    except Exception as exc:
        return {"error": str(exc)}
