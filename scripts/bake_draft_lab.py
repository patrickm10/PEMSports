"""Fail-open bake of Draft Lab parquet into the serving DuckDB.

Called at the end of scripts/bake_db.py. Missing parquet must not fail
rankings bake.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("bake_db")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFT_LAB_DIR = PROJECT_ROOT / "data" / "draft_lab"

TABLES = (
    ("draft_lab_leagues", "leagues.parquet", ("league_id",)),
    ("draft_lab_drafts", "drafts.parquet", ("draft_id", "league_id")),
    ("draft_lab_managers", "managers.parquet", ("manager_id", "league_id")),
    ("draft_lab_picks", "picks.parquet", ("draft_id", "player_id", "manager_id")),
    ("draft_lab_unresolved_players", "unresolved_players.parquet", ("draft_id",)),
    ("draft_lab_market", "market.parquet", ("player_id",)),
    ("draft_lab_manager_profiles", "manager_profiles.parquet", ("manager_id",)),
    ("draft_lab_backtests", "backtests.parquet", ("draft_id",)),
)


def bake_draft_lab_tables(conn) -> int:
    """Create draft_lab_* tables when parquet files exist. Returns tables created."""
    if not DRAFT_LAB_DIR.exists():
        logger.info("Draft Lab lake missing at %s — skip", DRAFT_LAB_DIR)
        return 0

    created = 0
    for table, filename, index_cols in TABLES:
        path = DRAFT_LAB_DIR / filename
        if not path.exists():
            continue
        path_str = str(path).replace("\\", "/")
        try:
            conn.execute(
                f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_parquet('{path_str}')"
            )
        except Exception as exc:  # noqa: BLE001 - fail-open per table
            logger.warning("Draft Lab table %s skipped (fail-open): %s", table, exc)
            continue
        existing = {
            d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description
        }
        for col in index_cols:
            if col not in existing:
                continue
            idx = f"idx_{table}_{col}"
            try:
                conn.execute(f"CREATE INDEX {idx} ON {table} ({col})")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Draft Lab index %s skipped: %s", idx, exc)
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("Baked %s: %s rows from %s", table, count, filename)
        created += 1
    if created == 0:
        logger.info("No Draft Lab parquet present — skip")
    return created
