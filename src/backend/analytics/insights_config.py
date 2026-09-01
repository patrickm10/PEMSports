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
