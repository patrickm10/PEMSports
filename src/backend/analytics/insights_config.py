"""
Configurable thresholds for PEM Insights v1.

All insight scoring uses these constants; adjust here rather than in SQL or React.
"""

# Minimum games in context required to appear on a leaderboard.
MIN_SAMPLE_SIZE = 3

# Sample strength labels (based on count only — not statistical confidence).
MODERATE_SAMPLE_SIZE = 5
STRONG_SAMPLE_SIZE = 8

# Sample weight for insight_score caps at 1.0 when sample_size >= this value.
FULL_WEIGHT_SAMPLE = 8

# Default leaderboard size per position group.
DEFAULT_LEADERBOARD_LIMIT = 15

# Supported insight positions (offensive skill positions only in v1).
INSIGHT_POSITIONS = ("qb", "rb", "wr", "te")

# Supported metrics (pipeline-owned fantasy points columns).
SUPPORTED_METRICS = ("fpts_ppr", "fpts")

DEFAULT_METRIC = "fpts_ppr"

# Elevation bands for Insights context `elevation`.
# Must match query_engine.py player-splits CASE until a later extract:
#   CASE WHEN elevation >= 500 THEN 'High'
#   WHEN elevation BETWEEN 100 AND 499 THEN 'Med'
#   ELSE 'Low' END
# Do not edit query_engine.py in the Insights location PR (ranking SQL contract).
ELEVATION_HIGH_MIN = 500
ELEVATION_MED_MIN = 100
CANONICAL_ELEVATION_VALUES = ("High", "Med", "Low")

# Weather buckets — specified, not registered in SUPPORTED_CONTEXTS until edges
# match the stored unit. Pipeline source is temp_C; baked column is `temp`.
# Gate 1 (2026-09-09): outdoor QB_weekly temp min/max/median = -16.2 / 38.0 / 15.8 °C.
# Do not apply the Fahrenheit edges below to these Celsius values.
WEATHER_TEMP_UNIT = "C"  # convert edges or values before registering `weather`
WEATHER_COLD_LT = 32  # Cold < 32°F — unused until unit is F or edges are converted
WEATHER_COOL_LT = 55  # Cool 32–54 → [32, 55)
WEATHER_MILD_LT = 80  # Mild 55–79 → [55, 80); Hot ≥ 80
CANONICAL_WEATHER_VALUES = ("Cold", "Cool", "Mild", "Hot", "Indoor")
CANONICAL_INDOOR_OUTDOOR_VALUES = ("Indoor", "Outdoor")
