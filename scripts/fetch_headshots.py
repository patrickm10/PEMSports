"""
Download or materialize player headshots into assets/players/{player_id}.png.

Your baked DuckDB uses internal hash-style player_id values (not ESPN numeric IDs),
so there is no single public URL pattern that maps 1:1 without an external ID table.

Modes:
  --placeholder (default)
      Copy default-player.png to each distinct player_id so the grid never 404s.
  --template URL
      HTTP GET for each id with {player_id} replaced (e.g. your CDN).
      Use --delay to throttle requests.

Examples (from repo root):
  python scripts/fetch_headshots.py --placeholder
  python scripts/fetch_headshots.py --template "https://cdn.example.com/players/{player_id}.png" --delay 0.1

Requires: duckdb (same env as bake_db.py)
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
PLAYERS_DIR = PROJECT_ROOT / "assets" / "players"
DEFAULT_FACE = PLAYERS_DIR / "default-player.png"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_headshots")


def _collect_player_ids() -> list[str]:
    import duckdb

    if not DB_PATH.exists():
        logger.error("Missing %s — run scripts/bake_db.py first.", DB_PATH)
        sys.exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        ids: set[str] = set()
        for t in tables:
            if not t.endswith(("_seasonal", "_weekly")):
                continue
            cols = {d[0].lower() for d in conn.execute(f"SELECT * FROM {t} LIMIT 0").description}
            if "player_id" not in cols:
                continue
            for (pid,) in conn.execute(
                f'SELECT DISTINCT player_id FROM {t} WHERE player_id IS NOT NULL'
            ).fetchall():
                if pid is None:
                    continue
                ids.add(str(pid).strip())
        return sorted(ids)
    finally:
        conn.close()


def _ensure_default_face() -> None:
    PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
    if not DEFAULT_FACE.exists():
        blank = PLAYERS_DIR / "blank-player.png"
        if blank.exists():
            shutil.copy2(blank, DEFAULT_FACE)
        else:
            logger.error("Missing %s — add a placeholder PNG first.", DEFAULT_FACE)
            sys.exit(1)


def run_placeholder(ids: list[str]) -> None:
    _ensure_default_face()
    for pid in ids:
        dest = PLAYERS_DIR / f"{pid}.png"
        shutil.copy2(DEFAULT_FACE, dest)
    logger.info("Copied default face to %d files under %s", len(ids), PLAYERS_DIR)


def run_template(ids: list[str], template: str, delay: float, timeout: int) -> None:
    _ensure_default_face()
    ok = 0
    for i, pid in enumerate(ids):
        url = template.replace("{player_id}", pid)
        dest = PLAYERS_DIR / f"{pid}.png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NFLStatsAnalyzer-fetch_headshots/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if not data:
                raise ValueError("empty body")
            dest.write_bytes(data)
            ok += 1
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as e:
            logger.warning("[%s] %s — using default face", pid, e)
            shutil.copy2(DEFAULT_FACE, dest)
        if delay > 0 and i + 1 < len(ids):
            time.sleep(delay)
    logger.info("Downloaded %d / %d (others fell back to default)", ok, len(ids))


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate assets/players from nfl_stats.db")
    parser.add_argument(
        "--template",
        type=str,
        default="",
        help='HTTP URL template with {player_id}, e.g. "https://cdn.example.com/{player_id}.png"',
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Seconds between HTTP requests when using --template",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Per-request timeout (seconds)",
    )
    args = parser.parse_args()

    ids = _collect_player_ids()
    logger.info("Found %d distinct player_id values", len(ids))
    if not ids:
        sys.exit(0)

    if args.template:
        run_template(ids, args.template, max(0.0, args.delay), args.timeout)
    else:
        run_placeholder(ids)


if __name__ == "__main__":
    main()
