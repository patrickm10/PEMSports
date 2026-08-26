"""Tests for context normalization helpers."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.analytics.context_normalization import (
    CANONICAL_SURFACE_VALUES,
    OBSERVED_SURFACE_VALUES,
    canonical_opponent_abbr,
    display_context_value,
    normalize_context_value,
    normalized_opponent_sql,
    normalized_surface_sql,
    observation_schema_keys,
)


def test_observed_surface_values_documented():
    assert OBSERVED_SURFACE_VALUES == ("Grass", "Turf")
    assert CANONICAL_SURFACE_VALUES == ("Grass", "Turf")


def test_surface_sql_maps_grass_and_turf():
    sql = normalized_surface_sql("surface_type")
    assert "'grass'" in sql.lower()
    assert "'turf'" in sql.lower()
    assert "ELSE NULL" in sql


def test_kc_and_slug_normalize_to_same_abbr():
    assert canonical_opponent_abbr("KC") == "KC"
    assert canonical_opponent_abbr("kc") == "KC"
    assert canonical_opponent_abbr("kansas_city_chiefs") == "KC"
    assert canonical_opponent_abbr("Kansas City Chiefs") == "KC"
    assert normalize_context_value("opponent", "KC") == normalize_context_value(
        "opponent", "kansas_city_chiefs"
    )
    assert display_context_value("opponent", "kansas_city_chiefs") == "KC"


def test_alias_abbreviations_collapse_to_canonical():
    assert canonical_opponent_abbr("JAC") == canonical_opponent_abbr("JAX")
    assert canonical_opponent_abbr("OAK") == canonical_opponent_abbr("LV")


def test_opponent_sql_maps_abbr_and_slug():
    sql = normalized_opponent_sql("opponent")
    assert "KC" in sql
    assert "kansas_city_chiefs" in sql
    assert "WHEN UPPER(TRIM(CAST(opponent AS VARCHAR))) = 'KC'" in sql


def test_observation_schema_keys_are_stable():
    keys = observation_schema_keys()
    for required in (
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
    ):
        assert required in keys
