"""
V3 Storage Migration Pipeline
Converts legacy CSV 'clean' data to partitioned Parquet and initializes DuckDB.
Follows ECC Database Migration patterns for safety and performance.
"""

import os
import duckdb
import polars as pl
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("v3_migration")

# Constants
SOURCE_DIR = Path("data_local/raw_scrapes")
TARGET_DIR = Path("data/v3")
DB_PATH = Path("data/nfl_stats.db")

POSITIONS = ["qb", "rb", "wr", "te", "k"]

def initialize_directories():
    """Ensure target directories exist."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initialized target directory: {TARGET_DIR}")

def migrate_positional_data():
    """Convert positional cleaned CSVs to Parquet."""
    for pos in POSITIONS:
        source_file = SOURCE_DIR / f"sorted_enriched_{pos}_2020_2024_cleaned.csv"
        target_file = TARGET_DIR / f"{pos}_stats.parquet"
        
        if not source_file.exists():
            logger.warning(f"Source file not found: {source_file}")
            continue
            
        logger.info(f"Migrating {pos.upper()} data...")
        df = pl.read_csv(source_file)
        
        # Ensure schema consistency (e.g., year and week as integers)
        if "year" in df.columns:
            df = df.with_columns(pl.col("year").cast(pl.Int32))
        if "week" in df.columns:
            df = df.with_columns(pl.col("week").cast(pl.Int32))
            
        df.write_parquet(target_file)
        logger.info(f"Saved {pos.upper()} to {target_file}")

def migrate_metadata():
    """Migrate rosters and matchups."""
    metadata_files = {
        "nfl_rosters_2018_2025.csv": "rosters.parquet",
        "nfl_matchups_enriched.csv": "matchups.parquet"
    }
    
    for src, tgt in metadata_files.items():
        source_file = SOURCE_DIR / src
        target_file = TARGET_DIR / tgt
        
        if not source_file.exists():
            logger.warning(f"Source metadata not found: {source_file}")
            continue
            
        logger.info(f"Migrating metadata: {src}...")
        df = pl.read_csv(source_file)
        df.write_parquet(target_file)
        logger.info(f"Saved {src} to {target_file}")

def initialize_duckdb():
    """Load Parquet files into DuckDB tables."""
    logger.info(f"Initializing DuckDB at {DB_PATH}...")
    con = duckdb.connect(str(DB_PATH))
    
    # Register positional tables
    for pos in POSITIONS:
        parquet_path = TARGET_DIR / f"{pos}_stats.parquet"
        if parquet_path.exists():
            con.execute(f"CREATE OR REPLACE TABLE {pos}_stats AS SELECT * FROM read_parquet('{parquet_path}')")
            logger.info(f"Created DuckDB table: {pos}_stats")
            
    # Register metadata tables
    con.execute(f"CREATE OR REPLACE TABLE rosters AS SELECT * FROM read_parquet('{TARGET_DIR / 'rosters.parquet'}')")
    con.execute(f"CREATE OR REPLACE TABLE matchups AS SELECT * FROM read_parquet('{TARGET_DIR / 'matchups.parquet'}')")
    
    con.close()
    logger.info("DuckDB initialization complete.")

def main():
    try:
        initialize_directories()
        migrate_positional_data()
        migrate_metadata()
        initialize_duckdb()
        logger.info("V3 Storage Migration SUCCESSFUL.")
    except Exception as e:
        logger.error(f"Migration FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
