"""
Shared constants for NFL pipelines.
Single source of truth for team mappings, positions, and scoring rules.
"""

from typing import Dict

# Abbreviation → full snake_case team name
TEAM_MAP: Dict[str, str] = {
    "ARI": "arizona_cardinals",
    "ATL": "atlanta_falcons",
    "BAL": "baltimore_ravens",
    "BUF": "buffalo_bills",
    "CAR": "carolina_panthers",
    "CHI": "chicago_bears",
    "CIN": "cincinnati_bengals",
    "CLE": "cleveland_browns",
    "DAL": "dallas_cowboys",
    "DEN": "denver_broncos",
    "DET": "detroit_lions",
    "FA":  "free_agent",
    "GB":  "green_bay_packers",
    "HOU": "houston_texans",
    "IND": "indianapolis_colts",
    "JAX": "jacksonville_jaguars",
    "JAC": "jacksonville_jaguars",
    "KC":  "kansas_city_chiefs",
    "LV":  "las_vegas_raiders",
    "OAK": "las_vegas_raiders",
    "LAC": "los_angeles_chargers",
    "SD":  "los_angeles_chargers",
    "LAR": "los_angeles_rams",
    "STL": "los_angeles_rams",
    "MIA": "miami_dolphins",
    "MIN": "minnesota_vikings",
    "NE":  "new_england_patriots",
    "NO":  "new_orleans_saints",
    "NYG": "new_york_giants",
    "NYJ": "new_york_jets",
    "PHI": "philadelphia_eagles",
    "PIT": "pittsburgh_steelers",
    "SF":  "san_francisco_49ers",
    "SEA": "seattle_seahawks",
    "TB":  "tampa_bay_buccaneers",
    "TEN": "tennessee_titans",
    "WAS": "washington_commanders",
    "WSH": "washington_commanders",
}

OFFENSIVE_POSITIONS = ["QB", "RB", "WR", "TE", "K"]

# ESPN PPR scoring rules per position.
# Keys are column names as they appear in the scraped DataFrame.
SCORING_RULES: Dict[str, Dict[str, float]] = {
    "QB": {
        "YDS": 0.05,       # passing yards
        "TD": 4.0,         # passing TD
        "INT": -2.0,       # interception
        "R_YDS": 0.1,      # rushing yards  (R_ prefix = rushing duplicate cols)
        "R_TD": 6.0,       # rushing TD
    },
    "RB": {
        "YDS": 0.1,        # rushing yards
        "TD": 6.0,         # rushing TD
        "REC": 1.0,        # reception (PPR)
        "R_YDS": 0.1,      # receiving yards
        "R_TD": 6.0,       # receiving TD
    },
    "WR": {
        "REC": 1.0,        # reception (PPR)
        "YDS": 0.1,        # receiving yards
        "TD": 6.0,         # receiving TD
    },
    "TE": {
        "REC": 1.0,        # reception (PPR)
        "YDS": 0.1,        # receiving yards
        "TD": 6.0,         # receiving TD
    },
    "K": {
        "FGM": 3.0,        # field goal made
        "FG MISS": -1.0,   # field goal missed
        "XPM": 1.0,        # extra point made
    },
}
