import argparse
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
POSITIONS = ["qb", "rb", "wr", "te", "k", "dst"]

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


def main(years: Iterable[int] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    year_list = list(years) if years is not None else list(YEARS)
    scoped = set(year_list) != set(YEARS)
    expected = _expected_years(year_list)
    for pos in POSITIONS:
        collected: list[pl.DataFrame] = []
        for year in tqdm(year_list, desc=f"{pos.upper()} Season Stats"):
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
        if scoped and out_parquet.exists():
            existing = pl.read_parquet(out_parquet)
            if "year" in existing.columns:
                existing = existing.filter(~pl.col("year").cast(pl.Int64).is_in(list(expected)))
            final_df = pl.concat([existing, final_df], how="diagonal")
            logging.info("[%s] merged seasonal year(s) %s into existing parquet", pos.upper(), sorted(expected))

        tmp_path = out_parquet.with_suffix(out_parquet.suffix + ".tmp")
        final_df.write_parquet(tmp_path)
        tmp_path.replace(out_parquet)
        logging.info(f"[{pos.upper()}] wrote consolidated {out_parquet}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape FantasyPros seasonal rankings.")
    parser.add_argument("--year", type=int, default=None, help="Single season year (default: 2020-2025).")
    args = parser.parse_args()
    main(years=[args.year] if args.year is not None else None)

