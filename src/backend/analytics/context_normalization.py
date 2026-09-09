"""
Context value normalization for PEM Insights.

Surface audit (2026-08-25, data/nfl_stats.db across qb/rb/wr/te weekly tables):
  - Observed distinct values: "Grass", "Turf" only (no other variants in baked data).
  - Normalization: case-insensitive trim; map to canonical Grass | Turf.
  - Unknown values → NULL (excluded from surface insights, never guessed).

Opponent identity matches Rankings: SQL groups by canonical TEAM_MAP abbreviation
(normalize_team_abbr). Stored slugs (kansas_city_chiefs) and abbreviations (KC)
resolve to the same group. API context values are those stable abbreviations.

Location (indoor_outdoor, elevation) uses ContextSpec: required baked columns plus
a SQL expression. Weather is specified (weather_bucket_sql) but not registered in
SUPPORTED_CONTEXTS until weekly `temp` has non-null coverage and a proven unit.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.analytics.insights_config import (
    CANONICAL_ELEVATION_VALUES,
    CANONICAL_INDOOR_OUTDOOR_VALUES,
    CANONICAL_WEATHER_VALUES,
    ELEVATION_HIGH_MIN,
    ELEVATION_MED_MIN,
    WEATHER_COLD_LT,
    WEATHER_COOL_LT,
    WEATHER_MILD_LT,
)
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


@dataclass(frozen=True)
class ContextSpec:
    """Insights dimension: required baked columns + closed vs open value set.

    SQL is produced by normalized_context_sql — derived contexts are not a
    single physical column.
    """

    name: str
    required_columns: tuple[str, ...]
    canonical_values: tuple[str, ...] | None  # closed set, or None for open


CONTEXT_SPECS: dict[str, ContextSpec] = {
    "surface": ContextSpec(
        name="surface",
        required_columns=("surface_type",),
        canonical_values=CANONICAL_SURFACE_VALUES,
    ),
    "opponent": ContextSpec(
        name="opponent",
        required_columns=("opponent",),
        canonical_values=None,
    ),
    "stadium": ContextSpec(
        name="stadium",
        required_columns=("stadium_name",),
        canonical_values=None,
    ),
    "home_away": ContextSpec(
        name="home_away",
        required_columns=("home_away",),
        canonical_values=("Home", "Away"),
    ),
    "indoor_outdoor": ContextSpec(
        name="indoor_outdoor",
        required_columns=("indoor_outdoor",),
        canonical_values=CANONICAL_INDOOR_OUTDOOR_VALUES,
    ),
    "elevation": ContextSpec(
        name="elevation",
        required_columns=("elevation",),
        canonical_values=CANONICAL_ELEVATION_VALUES,
    ),
}

SUPPORTED_CONTEXTS = tuple(CONTEXT_SPECS.keys())

_OBSERVATION_KEYS = (
    "season",
    "week",
    "opponent",
    "stadium_name",
    "surface_type",
    "home_away",
    "weather_bucket",
    "indoor_outdoor",
    "elevation_band",
    "fantasy_points",
    "season_baseline",
    "relative_change_pct",
    "in_context",
)


def observation_schema_keys() -> tuple[str, ...]:
    """Stable observation keys; missing values must be present as null."""
    return _OBSERVATION_KEYS


def context_spec(context: str) -> ContextSpec:
    spec = CONTEXT_SPECS.get(context)
    if spec is None:
        raise ValueError(f"Unsupported context: {context}")
    return spec


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_slugify_expr(column: str) -> str:
    """DuckDB expression matching Python opponent slug rules."""
    return (
        f"LOWER(REPLACE(REPLACE(REPLACE(TRIM(CAST({column} AS VARCHAR)), "
        f"' ', '_'), '.', ''), '''', ''))"
    )


def _qualify(table_alias: str, column: str) -> str:
    if table_alias:
        return f"{table_alias}.{column}"
    return column


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


def normalized_indoor_outdoor_sql(column: str = "indoor_outdoor") -> str:
    """DuckDB expression for Indoor | Outdoor | NULL. Unknown is never guessed."""
    return f"""
        CASE
            WHEN TRIM(LOWER({column})) = 'indoor' THEN 'Indoor'
            WHEN TRIM(LOWER({column})) = 'outdoor' THEN 'Outdoor'
            ELSE NULL
        END
    """.strip()


def elevation_band_sql(column: str = "elevation") -> str:
    """DuckDB expression for High | Med | Low | NULL.

    Edges are insights_config constants and must match query_engine.py
    player-splits CASE (elevation >= 500 High, 100–499 Med, else Low).
    NULL stays NULL — it must not become Low.
    """
    high = ELEVATION_HIGH_MIN
    med = ELEVATION_MED_MIN
    med_hi = ELEVATION_HIGH_MIN - 1
    return f"""
        CASE
            WHEN {column} IS NULL THEN NULL
            WHEN {column} >= {high} THEN 'High'
            WHEN {column} BETWEEN {med} AND {med_hi} THEN 'Med'
            ELSE 'Low'
        END
    """.strip()


def weather_bucket_sql(
    *,
    indoor_outdoor_column: str = "indoor_outdoor",
    temp_column: str = "temp",
) -> str:
    """DuckDB expression for Cold | Cool | Mild | Hot | Indoor | NULL.

    Indoor uses the same Indoor SQL as indoor_outdoor (shared). Outdoor null
    temp is excluded. Fahrenheit edges from insights_config — do not apply
    until WEATHER_TEMP_UNIT is proven. Not registered as an Insights context
    until weekly temp has outdoor non-null coverage.
    """
    indoor_expr = normalized_indoor_outdoor_sql(indoor_outdoor_column)
    return f"""
        CASE
            WHEN ({indoor_expr}) = 'Indoor' THEN 'Indoor'
            WHEN {temp_column} IS NULL THEN NULL
            WHEN CAST({temp_column} AS DOUBLE) < {WEATHER_COLD_LT} THEN 'Cold'
            WHEN CAST({temp_column} AS DOUBLE) < {WEATHER_COOL_LT} THEN 'Cool'
            WHEN CAST({temp_column} AS DOUBLE) < {WEATHER_MILD_LT} THEN 'Mild'
            ELSE 'Hot'
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


def normalized_context_sql(context: str, table_alias: str = "w") -> str:
    """Return SQL expression for the normalized context value.

    `table_alias` prefixes required columns (`w.elevation`). Pass \"\" when
    the query has no alias.
    """
    spec = context_spec(context)
    if context == "surface":
        return normalized_surface_sql(_qualify(table_alias, "surface_type"))
    if context == "home_away":
        return normalized_home_away_sql(_qualify(table_alias, "home_away"))
    if context == "stadium":
        return f"NULLIF(TRIM({_qualify(table_alias, 'stadium_name')}), '')"
    if context == "opponent":
        return normalized_opponent_sql(_qualify(table_alias, "opponent"))
    if context == "indoor_outdoor":
        return normalized_indoor_outdoor_sql(_qualify(table_alias, "indoor_outdoor"))
    if context == "elevation":
        return elevation_band_sql(_qualify(table_alias, "elevation"))
    raise ValueError(f"Unsupported context: {spec.name}")


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
    if context == "indoor_outdoor":
        low = value.strip().lower()
        if low == "indoor":
            return "Indoor"
        if low == "outdoor":
            return "Outdoor"
    if context == "elevation":
        low = value.strip().lower()
        if low in ("high", "h"):
            return "High"
        if low in ("med", "medium", "m"):
            return "Med"
        if low in ("low", "l"):
            return "Low"
    if context == "weather":
        # Follow-up context; keep value mapping ready without registering it.
        low = value.strip().lower()
        mapping = {v.lower(): v for v in CANONICAL_WEATHER_VALUES}
        if low in mapping:
            return mapping[low]
    return value.strip()


def display_context_value(context: str, value: str) -> str:
    """Normalize stored context keys for API responses."""
    if context == "opponent":
        return canonical_opponent_abbr(value)
    if context in ("surface", "home_away", "indoor_outdoor", "elevation", "weather"):
        return normalize_context_value(context, value)
    return value.strip()
