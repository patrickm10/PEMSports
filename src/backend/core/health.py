"""
Health check utilities.

Exposed at GET /health — verifies data files are present and readable
before declaring the service healthy. Downstream monitoring (Render,
UptimeRobot, etc.) should poll this endpoint, not the root path.
"""
from __future__ import annotations

import logging
from pathlib import Path

from backend.models.data_models import HealthResponse

logger = logging.getLogger(__name__)

# health.py is at src/backend/core/health.py → project root is 4 parents up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data" / "official_rankings" / "position"
POSITIONS = ["qb", "rb", "wr", "te", "k", "dst"]


def check_health() -> HealthResponse:
    """
    Validate data files exist and return structured health payload.
    Does NOT load data — just checks file presence. Fast enough for
    high-frequency polling.
    """
    available: list[str] = []

    for pos in POSITIONS:
        # Prefer Parquet, fall back to CSV
        parquet = _DATA_DIR / f"{pos.upper()}_historical.parquet"
        csv_file = _DATA_DIR / f"{pos.upper()}_historical.csv"
        if parquet.exists() or csv_file.exists():
            available.append(pos)

    status = "healthy" if available else "degraded"
    if not available:
        logger.error("Health check: no data files found in %s", _DATA_DIR)

    return HealthResponse(
        status=status,
        data_files_found=len(available),
        positions_available=available,
    )
