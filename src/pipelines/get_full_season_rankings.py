import logging
from pathlib import Path
from typing import Iterable

import polars as pl
from tqdm import tqdm

import sys

# Ensure 'src' is in sys.path for absolute imports like 'from pipelines...'
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipelines.transforms.get_new_nfl_data import get_fantasypros_data

# --- CONFIG --------------------------------------------------------

YEARS = range(2020, 2026)  # inclusive coverage: 2020–2025
POSITIONS = ["qb", "rb", "wr", "te", "k"]

OUTPUT_DIR = Path("data/rankings")
LOCAL_RAW_DIR = Path("data_local/raw_scrapes")


def _expected_years(years: Iterable[int]) -> set[int]:
    return {int(y) for y in years}

def _assert_year_coverage(df: pl.DataFrame, expected: set[int], *, pos: str) -> None:
    if "year" not in df.columns:
        raise RuntimeError(f"[{pos}] Seasonal ingestion missing required 'year' column; cannot validate completeness.")
    actual = {int(y) for y in df.get_column("year").unique().to_list()}
    missing_years = expected - actual
    if missing_years:
        raise RuntimeError(f"[{pos}] Incomplete seasonal ingestion: missing years {sorted(missing_years)}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    expected = _expected_years(YEARS)
    for pos in POSITIONS:
        collected: list[pl.DataFrame] = []
        for year in tqdm(YEARS, desc=f"{pos.upper()} Season Stats"):
            # Upstream fetch/transform. Must not silently succeed with partial years.
            df = get_fantasypros_data(pos.upper(), int(year), week=None)
            if df.is_empty():
                raise RuntimeError(f"[{pos.upper()}] Seasonal ingestion failed for year {year} (empty dataframe).")

            csv_name = f"{pos.upper()}_{year}_seasonal.csv"
            df.write_csv(LOCAL_RAW_DIR / csv_name)
            collected.append(df)

        if not collected:
            raise RuntimeError(f"[{pos.upper()}] No data collected for any year; failing pipeline.")

        final_df = pl.concat(collected, how="diagonal")
        _assert_year_coverage(final_df, expected, pos=pos.upper())

        out_parquet = OUTPUT_DIR / f"{pos.upper()}_seasonal.parquet"
        tmp_path = out_parquet.with_suffix(out_parquet.suffix + ".tmp")
        final_df.write_parquet(tmp_path)
        tmp_path.replace(out_parquet)
        logging.info(f"[{pos.upper()}] wrote consolidated {out_parquet}")


if __name__ == "__main__":
    main()

