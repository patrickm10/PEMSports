"""Attach headshot_url to ranking/search rows without rankings SQL JOINs.

Serving strategy:
- espn_player_id present → ESPN CDN combiner URL
- else → /headshots/{player_id}.jpg

Fail-open: missing `players` table or load errors → path-only URLs.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

PUBLIC_HEADSHOTS_ROUTE = "/headshots"

_espn_map_lock = threading.Lock()
_espn_map_cache: Optional[dict[str, str]] = None


def build_headshot_path(player_id: str) -> str:
    return f"{PUBLIC_HEADSHOTS_ROUTE}/{player_id}.jpg"


def build_espn_headshot_url(espn_player_id: str) -> str:
    eid = str(espn_player_id).strip()
    return (
        "https://a.espncdn.com/combiner/i"
        f"?img=/i/headshots/nfl/players/full/{eid}.png&h=96&w=96&scale=crop"
    )


def clear_espn_map_cache() -> None:
    global _espn_map_cache
    with _espn_map_lock:
        _espn_map_cache = None


def headshot_url_for(player_id: Any, espn_player_id: Any = None) -> str:
    pid = "" if player_id is None else str(player_id).strip()
    eid = "" if espn_player_id is None else str(espn_player_id).strip()
    if eid:
        return build_espn_headshot_url(eid)
    return build_headshot_path(pid) if pid else build_headshot_path("unknown")


def _load_espn_map(conn: Any) -> dict[str, str]:
    try:
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        if "players" not in tables:
            return {}
        cols = {d[0].lower() for d in conn.execute("SELECT * FROM players LIMIT 0").description}
        if "player_id" not in cols or "espn_player_id" not in cols:
            return {}
        rows = conn.execute(
            """
            SELECT CAST(player_id AS VARCHAR) AS player_id,
                   CAST(espn_player_id AS VARCHAR) AS espn_player_id
            FROM players
            WHERE espn_player_id IS NOT NULL
              AND CAST(espn_player_id AS VARCHAR) <> ''
            """
        ).fetchall()
        out: dict[str, str] = {}
        for pid, eid in rows:
            if pid is None or eid is None:
                continue
            ps, es = str(pid).strip(), str(eid).strip()
            if ps and es:
                out[ps] = es
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("headshot espn map load failed (fail-open): %s", exc)
        return {}


def get_espn_id_map(get_conn: Callable[[], Any]) -> dict[str, str]:
    global _espn_map_cache
    with _espn_map_lock:
        if _espn_map_cache is not None:
            return _espn_map_cache
        try:
            conn = get_conn()
            _espn_map_cache = _load_espn_map(conn)
        except Exception as exc:  # noqa: BLE001
            logger.warning("headshot espn map unavailable (fail-open): %s", exc)
            _espn_map_cache = {}
        return _espn_map_cache


def attach_headshot_urls(
    rows: list[dict[str, Any]],
    *,
    get_conn: Callable[[], Any],
    espn_map: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Mutate and return rows with headshot_url set (CDN when espn id known)."""
    if not rows:
        return rows
    mapping = espn_map if espn_map is not None else get_espn_id_map(get_conn)
    for row in rows:
        pid = row.get("player_id")
        eid = mapping.get(str(pid).strip()) if pid is not None else None
        row["headshot_url"] = headshot_url_for(pid, eid)
    return rows
