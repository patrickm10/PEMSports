"""
FantasyPros DST scraper — HTML in, raw Polars DataFrame out.
Dedicated to defensive rankings to isolate DOM dependencies.
"""

import logging
from typing import List

import polars as pl
from bs4 import BeautifulSoup

from pipelines.http_client import fetch_html

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://www.fantasypros.com/nfl/stats/dst.php"
    "?year={year}&scoring=PPR&range=full"
)


def scrape_dst_stats(year: int) -> pl.DataFrame:
    """
    Scrape full-season DST rankings for a given year.
    Returns a raw string-typed pl.DataFrame, or empty DataFrame on failure.
    """
    url = _BASE_URL.format(year=year)
    logger.info("Fetching raw DST rankings from: %s", url)

    html = fetch_html(url)
    if html is None:
        return pl.DataFrame()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "table"})
    
    if not table:
        logger.error("No data table found at %s", url)
        return pl.DataFrame()

    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    tbody = table.find("tbody")
    if tbody is None:
        logger.error("No <tbody> found at %s", url)
        return pl.DataFrame()

    rows = []
    for tr in tbody.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if tds:
            rows.append(tds)

    if not rows:
        logger.error("No DST data rows found at %s", url)
        return pl.DataFrame()

    if len(headers) != len(rows[0]):
        logger.error(
            "Header/row mismatch at %s: %d headers vs %d columns",
            url, len(headers), len(rows[0]),
        )
        return pl.DataFrame()

    df = pl.DataFrame(rows, orient="row", schema=headers)
    
    if df.is_empty():
        logger.error("Parsed DST DataFrame is empty for %s", url)
        
    return df
