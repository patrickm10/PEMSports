"""Service health — liveness plus serving-store availability."""
from __future__ import annotations

from backend.data.ranking_store import health_payload


def check_health() -> dict:
    """
    Returns service health and available data state.

    HTTP layer keeps 200 even when degraded so orchestrators (Render, etc.)
    can inspect `status` and `positions_available` in the body.
    """
    return health_payload()
