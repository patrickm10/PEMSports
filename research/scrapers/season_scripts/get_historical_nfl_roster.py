import logging
import os
import time
from itertools import product
from typing import Any, Dict, List, Optional

import polars as pl
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from pipelines.constants import TEAM_MAP

# Setup Logging
logger = logging.getLogger(__name__)

START_YEAR = 2018
END_YEAR = 2027
OUTPUT_DIR = "backend/static/data/nfl_metadata"
TIMEOUT = 15

# Map NFL.com URL slugs to standardized abbreviations
SLUG_TO_ABBR: Dict[str, str] = {
    "arizona-cardinals": "ARI",
    "atlanta-falcons": "ATL",
    "baltimore-ravens": "BAL",
    "buffalo-bills": "BUF",
    "carolina-panthers": "CAR",
    "chicago-bears": "CHI",
    "cincinnati-bengals": "CIN",
    "cleveland-browns": "CLE",
    "dallas-cowboys": "DAL",
    "denver-broncos": "DEN",
    "detroit-lions": "DET",
    "green-bay-packers": "GB",
    "houston-texans": "HOU",
    "indianapolis-colts": "IND",
    "jacksonville-jaguars": "JAX",
    "kansas-city-chiefs": "KC",
    "las-vegas-raiders": "LV",
    "los-angeles-chargers": "LAC",
    "los-angeles-rams": "LAR",
    "miami-dolphins": "MIA",
    "minnesota-vikings": "MIN",
    "new-england-patriots": "NE",
    "new-orleans-saints": "NO",
    "new-york-giants": "NYG",
    "new-york-jets": "NYJ",
    "philadelphia-eagles": "PHI",
    "pittsburgh-steelers": "PIT",
    "san-francisco-49ers": "SF",
    "seattle-seahawks": "SEA",
    "tampa-bay-buccaneers": "TB",
    "tennessee-titans": "TEN",
    "washington-commanders": "WAS",
}

def create_robust_session() -> requests.Session:
    """Creates a requests session with retries and exponential backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_historical_roster(
    session: requests.Session, year: int, slug: str
) -> Optional[pl.DataFrame]:
    """
    Return a DataFrame with columns: Player, Year, Team, Abbr.
    Logic aligned with ranking pipelines.
    """
    url = f"https://www.nfl.com/sitemap/html/rosters/{year}/{slug}"
    abbr = SLUG_TO_ABBR.get(slug, "UNK")
    
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.find("table", class_="d3-o-table")
        if not table:
            return None
            
        rows = table.find_all("tr")[1:]
        if not rows:
            return None

        data = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            
            link = cells[1].find("a")
            player_name = link.get_text(strip=True) if link else cells[1].get_text(strip=True)
            
            # Additional metadata if table structure allows (standardizing later)
            data.append({
                "Player": player_name,
                "Year": year,
                "Team_Slug": slug,
                "Abbr": abbr
            })

        return pl.DataFrame(data)

    except Exception as exc:
        logger.debug(f"Failed to fetch {year} {slug}: {exc}")
        return None

def display_roster_summary(df: pl.DataFrame) -> None:
    """Print a professional summary of the collected roster data."""
    if df.is_empty():
        print("\n❌ No roster data collected.")
        return

    print(f"\n{'='*50}")
    print(f"  NFL ROSTER COLLECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Total Players: {df.height:,}")
    print(f"Unique Teams:  {df['Abbr'].n_unique()}")
    print(f"Year Range:    {df['Year'].min()} - {df['Year'].max()}")
    
    # Yearly breakdown
    summary = df.group_by("Year").agg(pl.count("Player").alias("Count")).sort("Year")
    print(f"\nBreakdown by Year:")
    for row in summary.iter_rows(named=True):
        print(f"  {row['Year']}: {row['Count']:,} players")
    print(f"{'='*50}\n")

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    frames: List[pl.DataFrame] = []
    historical_years = range(START_YEAR, END_YEAR)
    pairs = list(product(SLUG_TO_ABBR.keys(), historical_years))
    
    session = create_robust_session()
    
    try:
        for slug, year in tqdm(
            pairs,
            desc="Scraping NFL Rosters",
            unit="combo"
        ):
            df = get_historical_roster(session, year, slug)
            if df is not None and df.height > 0:
                frames.append(df)
            
            # Subtle delay to avoid rate limiting
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.warning("\nExecution interrupted by user. Saving partial data...")

    if not frames:
        logger.error("No data collected across any year/team.")
        return

    combined = pl.concat(frames)
    
    # Standardize column for analytics pipeline (Abbr is useful for joins)
    combined = combined.select(["Player", "Year", "Abbr", "Team_Slug"])
    
    display_roster_summary(combined)

    filename = f"nfl_rosters_{START_YEAR}_{END_YEAR-1}.csv"
    out_path = os.path.join(OUTPUT_DIR, filename)
    combined.write_csv(out_path)
    
    logger.info(f"Successfully wrote {combined.height:,} records to {out_path}")

if __name__ == "__main__":
    main()

