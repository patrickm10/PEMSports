"""
Convert local seasonal CSV scrapes into serving Parquet.

Hard requirement: output must cover EXPECTED_YEARS. Partial CSV sets must
not silently overwrite a multi-year serving file (root cause of 2025-only
seasonal regression — see docs/agent_context/DATA_COVERAGE_AUDIT.md).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPECTED_YEARS = list(range(2020, 2026))  # 2020..2025 inclusive


def convert_seasonal_data(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    expected_years: list[int] | None = None,
) -> None:
    in_dir = in_dir or Path("data_local/raw_scrapes")
    out_dir = out_dir or Path("data/rankings")
    expected = set(expected_years or EXPECTED_YEARS)
    out_dir.mkdir(parents=True, exist_ok=True)

    positions = ["QB", "RB", "WR", "TE", "K"]
    for pos in positions:
        csv_files = list(in_dir.glob(f"{pos}_*_seasonal.csv"))
        if not csv_files:
            continue

        dfs: list[pd.DataFrame] = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:  # noqa: BLE001
                print(f"Skipping {f}: {e}")

        if not dfs:
            continue

        combined = pd.concat(dfs, ignore_index=True)
        if "year" not in combined.columns:
            raise ValueError(
                f"{pos}: seasonal CSV concat missing required 'year' column; "
                f"refusing to write {pos}_seasonal.parquet"
            )

        years_present = {
            int(y) for y in combined["year"].dropna().unique().tolist()
        }
        missing = sorted(expected - years_present)
        if missing:
            raise ValueError(
                f"{pos}: seasonal convert missing years {missing}; "
                f"present={sorted(years_present)}. Refusing overwrite of "
                f"{pos}_seasonal.parquet (expected {sorted(expected)})."
            )

        out_file = out_dir / f"{pos}_seasonal.parquet"
        combined.to_parquet(out_file, index=False)
        print(f"Successfully wrote {out_file} years={sorted(years_present)}")


if __name__ == "__main__":
    convert_seasonal_data()
