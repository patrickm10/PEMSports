"""Tests for context normalization helpers."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.analytics.context_normalization import (
    CANONICAL_SURFACE_VALUES,
    OBSERVED_SURFACE_VALUES,
    normalized_surface_sql,
)


def test_observed_surface_values_documented():
    assert OBSERVED_SURFACE_VALUES == ("Grass", "Turf")
    assert CANONICAL_SURFACE_VALUES == ("Grass", "Turf")


def test_surface_sql_maps_grass_and_turf():
    sql = normalized_surface_sql("surface_type")
    assert "'grass'" in sql.lower()
    assert "'turf'" in sql.lower()
    assert "ELSE NULL" in sql
