import os
from pathlib import Path
import polars as pl
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/official_rankings/position")

def convert_csv_to_parquet():
    if not DATA_DIR.exists():
        logger.error(f"Directory {DATA_DIR} does not exist.")
        return

    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {DATA_DIR}.")
        return

    for csv_file in csv_files:
        parquet_file = csv_file.with_suffix(".parquet")
        
        # Skip if parquet already exists (optional, could overwrite)
        # if parquet_file.exists():
        #     logger.info(f"Skipping {csv_file.name}, parquet already exists.")
        #     continue

        try:
            logger.info(f"Converting {csv_file.name} to Parquet...")
            df = pl.read_csv(csv_file)
            df.write_parquet(parquet_file)
            logger.info(f"Successfully created {parquet_file.name}")
        except Exception as e:
            logger.error(f"Failed to convert {csv_file.name}: {e}")

if __name__ == "__main__":
    convert_csv_to_parquet()
