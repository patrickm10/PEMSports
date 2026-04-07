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
# Strategy B Consolidated Store
_DATA_DIR = _PROJECT_ROOT / "data" / "rankings"
_FORECAST_DIR = _PROJECT_ROOT / "data" / "forecasts"
POSITIONS = ["qb", "rb", "wr", "te"]


def check_health() -> HealthResponse:
    """
    Validate Strategy B Parquet files and ML Forecasts exist.
    """
    available: list[str] = []
    forecasts: list[str] = []

    for pos in POSITIONS:
        # Check Strategy B Store (Consolidated Parquet)
        parquet = _DATA_DIR / f"{pos.upper()}_weekly.parquet"
        if parquet.exists():
            available.append(pos)
        
        # Check Weekly Alpha Forecasts
        forecast = _FORECAST_DIR / f"{pos.lower()}_alpha.parquet"
        if forecast.exists():
            forecasts.append(pos)

    # Health status based on core data availability
    status = "healthy" if len(available) == len(POSITIONS) else "degraded"
    
    # Informative logging for container monitoring
    if status == "degraded":
        logger.warning(f"Health: only {len(available)}/{len(POSITIONS)} core data files found.")

    return HealthResponse(
        status=status,
        data_files_found=len(available),
        positions_available=available,
        model_forecasts_ready=len(forecasts) == len(POSITIONS)
    )
