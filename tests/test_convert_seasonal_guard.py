"""
Unit tests for convert_seasonal year-coverage guard.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from convert_seasonal import EXPECTED_YEARS, convert_seasonal_data  # noqa: E402


def test_convert_refuses_partial_year_overwrite(tmp_path: Path):
    in_dir = tmp_path / "raw"
    out_dir = tmp_path / "rankings"
    in_dir.mkdir()
    out_dir.mkdir()

    # Pre-existing full-history serving file that must not be clobbered.
    full = pd.DataFrame(
        {
            "year": EXPECTED_YEARS,
            "player_name": [f"P{y}" for y in EXPECTED_YEARS],
            "fpts_ppr": [10.0] * len(EXPECTED_YEARS),
        }
    )
    existing = out_dir / "QB_seasonal.parquet"
    full.to_parquet(existing, index=False)

    # Only 2025 CSV present — classic regression input.
    pd.DataFrame(
        {"year": [2025], "player_name": ["Only2025"], "fpts_ppr": [99.0]}
    ).to_csv(in_dir / "QB_2025_seasonal.csv", index=False)

    with pytest.raises(ValueError, match="missing years"):
        convert_seasonal_data(in_dir=in_dir, out_dir=out_dir)

    # Existing parquet must remain untouched.
    kept = pd.read_parquet(existing)
    assert sorted(kept["year"].astype(int).unique()) == EXPECTED_YEARS


def test_convert_writes_when_all_years_present(tmp_path: Path):
    in_dir = tmp_path / "raw"
    out_dir = tmp_path / "rankings"
    in_dir.mkdir()
    out_dir.mkdir()

    for y in EXPECTED_YEARS:
        pd.DataFrame(
            {"year": [y], "player_name": [f"P{y}"], "fpts_ppr": [float(y)]}
        ).to_csv(in_dir / f"QB_{y}_seasonal.csv", index=False)

    convert_seasonal_data(in_dir=in_dir, out_dir=out_dir)
    out = pd.read_parquet(out_dir / "QB_seasonal.parquet")
    assert sorted(out["year"].astype(int).unique()) == EXPECTED_YEARS
