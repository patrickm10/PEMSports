"""
Team stat transforms — logic localized to team normalization.
"""

import logging
import re
from typing import Optional

import polars as pl

from pipelines.constants import TEAM_MAP

logger = logging.getLogger(__name__)


def extract_dst_team_abbr(raw_name: str) -> Optional[str]:
    """
    Extract abbreviation from DST name and map it to full team name.
    
    "Buffalo Bills (BUF)" -> "buffalo_bills"
    """
    if not isinstance(raw_name, str):
        return None
        
    match = re.search(r"\(([\w]+)\)", raw_name)
    if match:
        abbr = match.group(1).upper()
        return TEAM_MAP.get(abbr, abbr)
        
    return TEAM_MAP.get(raw_name.upper(), raw_name)
