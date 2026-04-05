import logging
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

# --- CONFIG --------------------------------------------------------

YEARS = range(2020, 2026)
POSITIONS = ["qb", "rb", "wr", "te", "k"]
BASE_URL = "https://www.fantasypros.com/nfl/stats/{pos}.php?year={year}"

OUTPUT_DIR = Path("data/rankings")
LOCAL_RAW_DIR = Path("data_local/raw_scrapes")

# ... helper functions remain the same ...

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for pos in POSITIONS:
        collected = []
        for year in tqdm(YEARS, desc=f"{pos.upper()} Season Stats"):
            url = BASE_URL.format(pos=pos, year=year)
            html = _fetch_html(url)
            if not html:
                continue

            df = _extract_table_data(BeautifulSoup(html, "html.parser"), pos, year)
            if df is not None:
                # Save CSV (Local/Fallback)
                csv_name = f"{pos.upper()}_{year}_seasonal.csv"
                df.to_csv(LOCAL_RAW_DIR / csv_name, index=False)
                collected.append(df)

        if not collected:
            logging.warning(f"No data collected for {pos}")
            continue

        final_df = pd.concat(collected, ignore_index=True)
        out_parquet = OUTPUT_DIR / f"{pos.upper()}_seasonal.parquet"
        final_df.to_parquet(out_parquet, index=False)
        logging.info(f"[{pos.upper()}] wrote consolidated {out_parquet}")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()

