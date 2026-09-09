"""Tests for context normalization helpers."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import duckdb

from backend.analytics.context_normalization import (
    CANONICAL_SURFACE_VALUES,
    CONTEXT_SPECS,
    OBSERVED_SURFACE_VALUES,
    SUPPORTED_CONTEXTS,
    canonical_opponent_abbr,
    display_context_value,
    elevation_band_sql,
    normalize_context_value,
    normalized_indoor_outdoor_sql,
    normalized_opponent_sql,
    normalized_surface_sql,
    observation_schema_keys,
    weather_bucket_sql,
)
from backend.analytics.insights_config import (
    ELEVATION_HIGH_MIN,
    ELEVATION_MED_MIN,
)

_QUERY_ENGINE = Path(__file__).resolve().parent.parent / "src" / "backend" / "data" / "query_engine.py"


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
        "weather_bucket",
        "indoor_outdoor",
        "elevation_band",
        "fantasy_points",
        "season_baseline",
        "relative_change_pct",
        "in_context",
    ):
        assert required in keys


def test_weather_is_not_a_supported_context():
    assert "weather" not in SUPPORTED_CONTEXTS
    assert "weather" not in CONTEXT_SPECS
    assert "indoor_outdoor" in CONTEXT_SPECS
    assert "elevation" in CONTEXT_SPECS


def test_indoor_normalization_unknown_is_null():
    sql = f"SELECT {normalized_indoor_outdoor_sql('v')} AS band FROM t"
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE t AS SELECT * FROM (VALUES "
        "('Indoor'), ('indoor'), ('Outdoor'), ('retractable'), (NULL), ('')) t(v)"
    )
    rows = [r[0] for r in con.execute(sql).fetchall()]
    assert rows == ["Indoor", "Indoor", "Outdoor", None, None, None]


def test_elevation_band_edges_match_rankings_case():
    src = _QUERY_ENGINE.read_text(encoding="utf-8")
    assert "WHEN elevation >= 500 THEN 'High'" in src
    assert "WHEN elevation BETWEEN 100 AND 499 THEN 'Med'" in src
    expr = elevation_band_sql("elev")
    assert str(ELEVATION_HIGH_MIN) in expr
    assert str(ELEVATION_MED_MIN) in expr
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE t AS SELECT * FROM (VALUES "
        "(99), (100), (499), (500), (NULL)) t(elev)"
    )
    rows = [r[0] for r in con.execute(f"SELECT {expr} FROM t").fetchall()]
    assert rows == ["Low", "Med", "Med", "High", None]


def test_weather_sql_shares_indoor_and_excludes_null_temp():
    expr = weather_bucket_sql(indoor_outdoor_column="io", temp_column="temp")
    indoor_sql = normalized_indoor_outdoor_sql("io")
    assert "Indoor" in indoor_sql
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE t AS SELECT * FROM (VALUES "
        "('Indoor', 70.0), ('Outdoor', NULL), ('Outdoor', 31.9), "
        "('Outdoor', 32.0), ('Outdoor', 54.9), ('Outdoor', 55.0), "
        "('Outdoor', 79.9), ('Outdoor', 80.0), ('retractable', 40.0)"
        ") t(io, temp)"
    )
    rows = [r[0] for r in con.execute(f"SELECT {expr} FROM t").fetchall()]
    assert rows == [
        "Indoor",
        None,
        "Cold",
        "Cool",
        "Cool",
        "Mild",
        "Mild",
        "Hot",
        "Cool",
    ]


def test_normalize_location_context_values():
    assert normalize_context_value("indoor_outdoor", "indoor") == "Indoor"
    assert normalize_context_value("elevation", "high") == "High"
    assert normalize_context_value("elevation", "med") == "Med"
