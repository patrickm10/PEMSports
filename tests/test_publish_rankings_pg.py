"""Coerce DuckDB float years so Neon INTEGER COPY succeeds."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "publish_rankings_pg",
    Path(__file__).resolve().parent.parent / "scripts" / "publish_rankings_pg.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_mod)


def test_coerce_float_year_to_int():
    assert _mod._coerce_copy_value("year", "DOUBLE", 2025.0) == 2025
    assert _mod._coerce_copy_value("week", "DOUBLE", "1.0") == 1
    assert _mod._coerce_copy_value("yds", "DOUBLE", 312.5) == 312.5
    assert _mod._coerce_copy_value("year", "INTEGER", None) is None
