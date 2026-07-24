"""Service health — liveness plus DuckDB serving-layer availability."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = Path(
    os.environ.get("NFL_STATS_DB_PATH", str(_PROJECT_ROOT / "data" / "nfl_stats.db"))
).resolve()


def check_health() -> dict:
    """
    Returns service health and available data state.

    HTTP layer keeps 200 even when degraded so orchestrators (Render, etc.)
    can inspect `status` and `positions_available` in the body.
    """
    positions_available: list[str] = []
    data_files_found = 0
    status = "ok"

    if not _DB_PATH.exists():
        status = "degraded"
    else:
        try:
            conn = duckdb.connect(str(_DB_PATH), read_only=True)
            tables = {row[0].lower() for row in conn.execute("SHOW TABLES").fetchall()}
            conn.close()

            for pos in POSITIONS:
                if f"{pos.lower()}_seasonal" in tables:
                    positions_available.append(pos)

            data_files_found = sum(
                1
                for pos in POSITIONS
                for kind in ("weekly", "seasonal")
                if f"{pos.lower()}_{kind}" in tables
            )

            if not positions_available:
                status = "degraded"
        except Exception:
            status = "degraded"

    return {
        "status": status,
        "version": "1.0.0",
        "service": "pem-sports-api",
        "data_files_found": data_files_found,
        "positions_available": positions_available,
    }
