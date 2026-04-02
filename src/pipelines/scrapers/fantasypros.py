"""
FantasyPros scraper — HTML in, raw Polars DataFrame out.
No data cleaning or transformation; that belongs in transforms/.
"""

import logging
from typing import List, Optional

import polars as pl
from bs4 import BeautifulSoup

from pipelines.http_client import fetch_html

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.fantasypros.com/nfl/stats/{position}.php"


def _rename_duplicate_headers(headers: List[str]) -> List[str]:
    """
    Deduplicate column names by prefixing subsequent occurrences with 'R_'.

    Example:
        ['PLAYER', 'ATT', 'YDS', 'ATT', 'YDS']
        → ['PLAYER', 'ATT', 'YDS', 'R_ATT', 'R_YDS']
    """
    seen: set[str] = set()
    result: List[str] = []
    for h in headers:
        if h in seen:
            result.append(f"R_{h}")
        else:
            result.append(h)
            seen.add(h)
    return result


def scrape_positional_stats(
    position: str, year: int, week: Optional[int] = None
) -> pl.DataFrame:
    """
    Scrape a single position/year table from FantasyPros.

    When `week` is provided, fetches weekly stats for that specific week.
    Otherwise fetches full-season totals.

    Returns a raw string-typed pl.DataFrame with deduplicated headers,
    or an empty DataFrame on failure.
    """
    url = _BASE_URL.format(position=position.lower())
    if week is not None:
        url += f"?week={week}&range=week&year={year}"
    else:
        url += f"?scoring=PPR&year={year}"

    html = fetch_html(url)
    if html is None:
        return pl.DataFrame()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "table"})
    if not table:
        logger.error("No data table found at %s", url)
        return pl.DataFrame()

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    headers = _rename_duplicate_headers(headers)

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
        logger.error("No player rows found at %s", url)
        return pl.DataFrame()

    if len(headers) != len(rows[0]):
        logger.error(
            "Header/row mismatch at %s: %d headers vs %d columns",
            url, len(headers), len(rows[0]),
        )
        return pl.DataFrame()

    # Explicit column validation
    required_substr = ["Player", "PLAYER"] 
    has_player_col = any(any(sub in h for sub in required_substr) for h in headers)
    if not has_player_col:
        logger.error("Scraper failed validation: Expected a column containing 'Player' but got %r", headers)
        return pl.DataFrame()

    return pl.DataFrame(rows, orient="row", schema=headers)

