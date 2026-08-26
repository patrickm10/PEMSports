"""
Context value normalization for PEM Insights.

Surface audit (2026-08-25, data/nfl_stats.db across qb/rb/wr/te weekly tables):
  - Observed distinct values: "Grass", "Turf" only (no other variants in baked data).
  - Normalization: case-insensitive trim; map to canonical Grass | Turf.
  - Unknown values → NULL (excluded from surface insights, never guessed).
"""

from __future__ import annotations

from backend.utils.team_normalization import normalize_team_abbr
from constants import TEAM_MAP

# Documented surface normalization decisions (from historical dataset inspection).
OBSERVED_SURFACE_VALUES = ("Grass", "Turf")
CANONICAL_SURFACE_VALUES = ("Grass", "Turf")

CONTEXT_COLUMN_MAP: dict[str, str] = {
    "surface": "surface_type",
    "opponent": "opponent",
    "stadium": "stadium_name",
    "home_away": "home_away",
}

SUPPORTED_CONTEXTS = tuple(CONTEXT_COLUMN_MAP.keys())


def normalized_surface_sql(column: str = "surface_type") -> str:
    """
    DuckDB expression mapping surface_type → Grass | Turf | NULL.

    Only observed variants (Grass, Turf) normalize; everything else is NULL.
    """
    return f"""
        CASE
            WHEN TRIM(LOWER({column})) = 'grass' THEN 'Grass'
            WHEN TRIM(LOWER({column})) = 'turf' THEN 'Turf'
            ELSE NULL
        END
    """.strip()


def normalized_home_away_sql(column: str = "home_away") -> str:
    """DuckDB expression for Home | Away | NULL."""
    return f"""
        CASE
            WHEN TRIM(LOWER({column})) IN ('home', 'h') THEN 'Home'
            WHEN TRIM(LOWER({column})) IN ('away', 'a') THEN 'Away'
            ELSE NULL
        END
    """.strip()


def normalized_context_sql(context: str, raw_column: str) -> str:
    """Return SQL expression for the normalized context value column."""
    if context == "surface":
        return normalized_surface_sql(raw_column)
    if context == "home_away":
        return normalized_home_away_sql(raw_column)
    if context == "stadium":
        return f"NULLIF(TRIM({raw_column}), '')"
    # opponent: normalized at API serialize boundary; use raw column for grouping
    return f"NULLIF(TRIM(CAST({raw_column} AS VARCHAR)), '')"


def context_column(context: str) -> str:
    """Physical column name for a context dimension."""
    col = CONTEXT_COLUMN_MAP.get(context)
    if col is None:
        raise ValueError(f"Unsupported context: {context}")
    return col


def opponent_slug(raw: str) -> str:
    """Map abbreviation or slug input to TEAM_MAP slug for DB matching."""
    up = str(raw).strip().upper()
    if up in TEAM_MAP:
        return TEAM_MAP[up]
    return (
        str(raw)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace("'", "")
    )


def normalize_context_value(context: str, value: str) -> str:
    """Normalize user-facing context_value to DB comparison form."""
    if context == "opponent":
        return opponent_slug(value)
    if context == "surface":
        low = value.strip().lower()
        if low == "grass":
            return "Grass"
        if low == "turf":
            return "Turf"
    if context == "home_away":
        low = value.strip().lower()
        if low in ("home", "h"):
            return "Home"
        if low in ("away", "a"):
            return "Away"
    return value.strip()


def display_context_value(context: str, value: str) -> str:
    """Normalize stored context keys for API responses."""
    if context == "opponent":
        return normalize_team_abbr(value) or value
    return value
