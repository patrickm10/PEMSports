"""
Context value normalization for PEM Insights.

Surface audit (2026-08-25, data/nfl_stats.db across qb/rb/wr/te weekly tables):
  - Observed distinct values: "Grass", "Turf" only (no other variants in baked data).
  - Normalization: case-insensitive trim; map to canonical Grass | Turf.
  - Unknown values → NULL (excluded from surface insights, never guessed).

Opponent identity matches Rankings: SQL groups by canonical TEAM_MAP abbreviation
(normalize_team_abbr). Stored slugs (kansas_city_chiefs) and abbreviations (KC)
resolve to the same group. API context values are those stable abbreviations.
"""

from __future__ import annotations

from backend.utils.team_normalization import normalize_team_abbr
from constants import TEAM_MAP

# First TEAM_MAP abbreviation per slug is the canonical identity (JAX not JAC, LV not OAK).
_SLUG_TO_CANON_ABBR: dict[str, str] = {}
for _abbr, _slug in TEAM_MAP.items():
    if _slug not in _SLUG_TO_CANON_ABBR:
        _SLUG_TO_CANON_ABBR[_slug] = _abbr

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

_OBSERVATION_KEYS = (
    "season",
    "week",
    "opponent",
    "stadium_name",
    "surface_type",
    "home_away",
    "fantasy_points",
    "season_baseline",
    "relative_change_pct",
    "in_context",
)


def observation_schema_keys() -> tuple[str, ...]:
    """Stable observation keys; missing values must be present as null."""
    return _OBSERVATION_KEYS


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_slugify_expr(column: str) -> str:
    """DuckDB expression matching Python opponent slug rules."""
    return (
        f"LOWER(REPLACE(REPLACE(REPLACE(TRIM(CAST({column} AS VARCHAR)), "
        f"' ', '_'), '.', ''), '''', ''))"
    )


def canonical_opponent_abbr(raw: str) -> str:
    """Map abbreviation, slug, or team name to the canonical TEAM_MAP abbreviation.

    Alias keys (JAC/JAX, OAK/LV) collapse to the first abbreviation for that slug
    so SQL grouping matches Rankings team identity rather than raw stored strings.
    """
    s = str(raw).strip()
    if not s:
        return s
    up = s.upper()
    if up in TEAM_MAP:
        return _SLUG_TO_CANON_ABBR[TEAM_MAP[up]]
    mapped = normalize_team_abbr(s)
    if mapped is None:
        return s
    mapped_up = str(mapped).strip().upper()
    if mapped_up in TEAM_MAP:
        return _SLUG_TO_CANON_ABBR[TEAM_MAP[mapped_up]]
    return str(mapped)


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


def normalized_opponent_sql(column: str = "opponent") -> str:
    """
    DuckDB expression mapping opponent identifiers to canonical abbreviations.

    Groups KC / kansas_city_chiefs / Kansas City Chiefs together. Unknown values
    keep their trimmed raw form (never guessed into a team).
    """
    slug_expr = _sql_slugify_expr(column)
    seen_slugs: set[str] = set()
    clauses: list[str] = []

    for abbr, slug in TEAM_MAP.items():
        canonical = canonical_opponent_abbr(abbr)
        clauses.append(
            f"WHEN UPPER(TRIM(CAST({column} AS VARCHAR))) = {_sql_literal(abbr)} "
            f"THEN {_sql_literal(canonical)}"
        )
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        clauses.append(
            f"WHEN {slug_expr} = {_sql_literal(slug)} THEN {_sql_literal(canonical)}"
        )

    joined = "\n            ".join(clauses)
    return f"""
        CASE
            {joined}
            ELSE NULLIF(TRIM(CAST({column} AS VARCHAR)), '')
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
    if context == "opponent":
        return normalized_opponent_sql(raw_column)
    return f"NULLIF(TRIM(CAST({raw_column} AS VARCHAR)), '')"


def context_column(context: str) -> str:
    """Physical column name for a context dimension."""
    col = CONTEXT_COLUMN_MAP.get(context)
    if col is None:
        raise ValueError(f"Unsupported context: {context}")
    return col


def opponent_slug(raw: str) -> str:
    """Map abbreviation or slug input to TEAM_MAP slug (legacy helper)."""
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
    """Normalize user-facing context_value to the SQL comparison form."""
    if context == "opponent":
        return canonical_opponent_abbr(value)
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
        return canonical_opponent_abbr(value)
    if context == "surface":
        return normalize_context_value("surface", value)
    if context == "home_away":
        return normalize_context_value("home_away", value)
    return value.strip()
