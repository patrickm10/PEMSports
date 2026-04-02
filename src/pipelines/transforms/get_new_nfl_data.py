"""
NFL Offensive Stats Scraper (FantasyPros)
Author: Patrick Mejia (Refactored)
Date: 2026-03-23
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import polars as pl
import re
import logging
import os
from collections import Counter
from typing import Optional, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_player_name_team(raw_name: str):
    """
    Input: "Josh Allen (BUF)" or "Josh Allen (BUF) K"
    Output: ("Josh Allen", "BUF")
    """
    match = re.search(r"(.*?)\s*\((.*?)\)", raw_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return raw_name.strip(), "FA"

def get_fantasypros_data(position: str, year: int, week: Optional[int] = None) -> pl.DataFrame:
    """
    Scrapes FantasyPros stats for a given position, year, and optionally week.
    Returns a Polars DataFrame with standardized column names.
    """
    pos = position.lower()
    
    # FantasyPros URL rules:
    # Weekly views drop 'scoring' param for position players and require range=week BEFORE year for some edge cases.
    if week:
        url = f"https://www.fantasypros.com/nfl/stats/{pos}.php?week={week}&range=week&year={year}"
    else:
        # FantasyPros uses different scoring param for DST in seasonal mode
        scoring = "DST" if pos == "dst" else "PPR"
        url = f"https://www.fantasypros.com/nfl/stats/{pos}.php?scoring={scoring}&year={year}"
    
    logger.info(f"Scraping {position} for {year}{' Week '+str(week) if week else ''} from {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", {"id": "data"})
        if not table:
            # Fallback for dynamic IDs
            table = soup.find("table", {"class": "table"})
        
        if not table:
            logger.error(f"No table found for {position} {year}")
            return pl.DataFrame()

        # Extract headers and handle duplicates
        thead_rows = table.find("thead").find_all("tr")
        target_header_row = thead_rows[-1] if thead_rows else table.find("thead")
        raw_headers = [th.text.strip() for th in target_header_row.find_all("th")]
        header_counts = Counter()
        headers = []
        for h in raw_headers:
            if not h: h = "EXTRA"
            if header_counts[h] > 0:
                headers.append(f"R_{h}" if header_counts[h] == 1 else f"R{header_counts[h]}_{h}")
            else:
                headers.append(h)
            header_counts[h] += 1

        # Extract data
        rows = []
        for tr in table.find("tbody").find_all("tr"):
            cols = [td.text.strip() for td in tr.find_all("td")]
            if len(cols) == len(headers):
                rows.append(cols)

        if not rows:
            return pl.DataFrame()

        df = pl.DataFrame(rows, schema=headers, orient="row")
        
        # Standardize Names and Teams
        if "Player" in df.columns:
            name_team = [clean_player_name_team(n) for n in df["Player"]]
            df = df.with_columns([
                pl.Series("player_name", [nt[0] for nt in name_team]),
                pl.Series("team", [nt[1] for nt in name_team]),
                pl.lit(position.upper()).alias("position"),
                pl.lit(year, dtype=pl.Int64).alias("year")
            ])
            
        # Standardize numeric columns
        for col in df.columns:
            if col not in ["player_name", "team", "position", "Player", "player_id", "year", "week"]:
                # Remove commas and convert to float
                df = df.with_columns(
                    pl.col(col).cast(pl.Utf8).str.replace_all(",", "").str.replace_all("%", "").cast(pl.Float64, strict=False).fill_null(0.0)
                )

        # Mapping for unified schema
        # Standard schema used by the app: ["year", "player_id", "player_name", "team", "position", "games_played", "fpts", "fpts_ppr", "fpts_per_game", "fpts_ppr_per_game", "yds", "td"]
        schema_map = {
            "G": "games_played",
            "FPTS": "fpts_ppr",
            "FPTS/G": "fpts_ppr_per_game",
        }
        
        # Position-specific stats
        if pos == "qb":
            schema_map.update({"YDS": "yds", "TD": "td"})
        elif pos in ["rb", "wr", "te"]:
            schema_map.update({"YDS": "yds", "TD": "td", "REC": "rec", "TGT": "targets"})
        elif pos == "k":
            schema_map.update({"FG": "yds", "FGA": "td"})
        elif pos == "dst":
            schema_map.update({"SACK": "yds", "INT": "td"}) # Placeholder mapping for DST

        rename_dict = {k: v for k, v in schema_map.items() if k in df.columns}
        df = df.rename(rename_dict)
        
        if "fpts_ppr" in df.columns:
            if "REC" in df.columns:
                df = df.with_columns((pl.col("fpts_ppr") - pl.col("REC")).alias("fpts"))
            else:
                df = df.with_columns(pl.col("fpts_ppr").alias("fpts"))
            
            df = df.with_columns((pl.col("fpts") / pl.col("games_played")).round(2).alias("fpts_per_game"))
            
        # Create a stable player_id from name and team
        import hashlib
        def stable_hash(n, t): return hashlib.md5(f"{n}_{t}".lower().encode()).hexdigest()
        df = df.with_columns(pl.struct(["player_name", "team"]).map_elements(lambda x: stable_hash(x["player_name"], x["team"]), return_dtype=pl.Utf8).alias("player_id"))

        return df

    except Exception as e:
        logger.error(f"Error scraping {position} {year}: {e}")
        return pl.DataFrame()

def run_full_scraping_verification():
    """Verifies that data for 2020-2026 exists for all positions."""
    years = range(2020, 2027)
    positions = ["QB", "RB", "WR", "TE", "K"]
    
    summary = []
    for year in years:
        for pos in positions:
            df = get_fantasypros_data(pos, year)
            count = len(df)
            summary.append({"year": year, "pos": pos, "count": count})
            print(f"[{year}] {pos}: {count} records scraped.")
            
            # Save check - ensure data/official_rankings exists
            if count > 0:
                os.makedirs("data/official_rankings/position", exist_ok=True)
                out_path = f"data/official_rankings/position/{pos}_historical.csv"
                # For verification, we just print the first entry
                # print(df.head(1))

    summary_df = pl.DataFrame(summary)
    print("\nScraping Summary (2020-2026):")
    print(summary_df.pivot(values="count", index="year", columns="pos", aggregate_function="first"))

if __name__ == "__main__":
    run_full_scraping_verification()
