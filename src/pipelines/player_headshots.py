"""
Download ESPN CDN headshots keyed by canonical internal UUID `player_id`.

Contract:
- Assets are stored as: data/headshots/{player_id}.jpg
- Public path is:       /headshots/{player_id}.jpg
- No name-based matching is allowed in this pipeline. All joins must use `player_id`.

Source-of-truth:
- DuckDB table `players` baked into data/nfl_stats.db (see scripts/bake_db.py),
  containing `player_id` (UUID) and nullable `espn_player_id`.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

import duckdb

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "data" / "nfl_stats.db"
_DEFAULT_OUTPUT = _REPO_ROOT / "data" / "player_headshots.csv"
_DEFAULT_HEADSHOTS_DIR = _REPO_ROOT / "data" / "headshots"
_LOG_PATH = _REPO_ROOT / "logs" / "pipelines" / "player_headshots.log"

PUBLIC_HEADSHOTS_ROUTE = "/headshots"
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}

_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    log = logging.getLogger("pipelines.player_headshots")
    if log.handlers:
        _logger = log
        return log

    log.setLevel(logging.DEBUG)
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(str(_LOG_PATH), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    log.addHandler(fh)
    log.addHandler(ch)
    log.propagate = False
    _logger = log
    return log


logger = get_logger()


def repo_root() -> Path:
    return _REPO_ROOT


def build_headshot_path(player_id: str) -> str:
    return f"{PUBLIC_HEADSHOTS_ROUTE}/{player_id}.jpg"


def build_espn_headshot_url(espn_player_id: str, *, raw: bool = False) -> str:
    eid = str(espn_player_id).strip()
    if raw:
        return f"https://a.espncdn.com/i/headshots/nfl/players/full/{eid}.png"
    return (
        "https://a.espncdn.com/combiner/i"
        f"?img=/i/headshots/nfl/players/full/{eid}.png&h=96&w=96&scale=crop"
    )


def collect_players_with_external_ids(db_path: Path) -> List[Dict[str, str]]:
    if not db_path.exists():
        raise FileNotFoundError(f"Missing database: {db_path}")

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        if "players" not in tables:
            raise ValueError(
                "Missing `players` table in serving DB. "
                "Create data/players.csv, then rebake with scripts/bake_db.py."
            )

        rows = conn.execute(
            """
            SELECT
              CAST(player_id AS VARCHAR) AS player_id,
              CAST(NULLIF(espn_player_id, '') AS VARCHAR) AS espn_player_id,
              CAST(player_name AS VARCHAR) AS player_name,
              CAST(team AS VARCHAR) AS team,
              CAST(position AS VARCHAR) AS position
            FROM players
            WHERE player_id IS NOT NULL
            """
        ).fetchall()

        out: list[dict[str, str]] = []
        for pid, espn_id, name, team, pos in rows:
            out.append(
                {
                    "player_id": (pid or "").strip(),
                    "espn_player_id": (espn_id or "").strip(),
                    "player_name": (name or "").strip(),
                    "team": (team or "").strip(),
                    "position": (pos or "").strip(),
                }
            )
        return sorted(out, key=lambda r: r["player_id"])
    finally:
        conn.close()


def _download_bytes(url: str, *, timeout: int) -> bytes | None:
    resp = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
    if resp.status_code != 200 or not resp.content:
        logger.warning("Image download failed %s status=%s", url, resp.status_code)
        return None
    return resp.content


def _png_to_jpeg(png_bytes: bytes) -> bytes:
    """
    Convert a PNG payload to JPEG bytes.

    ESPN headshots are PNG but our asset contract is .jpg.
    """
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Pillow is required to write .jpg headshots. Install Pillow.") from exc

    import io

    with Image.open(io.BytesIO(png_bytes)) as im:
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=90, optimize=True, progressive=True)
        return out.getvalue()


def run_pipeline(
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    delay: float = 0.05,
    timeout: int = 15,
    limit: Optional[int] = None,
    db_path: Optional[Path] = None,
    output_csv: Optional[Path] = None,
    headshots_dir: Optional[Path] = None,
    validation_mode: bool = False,
) -> List[Dict[str, str]]:
    """
    Download ESPN CDN headshots keyed by canonical UUID `player_id`.

    Only players with a non-empty `players.espn_player_id` will be downloaded.
    """
    db = Path(db_path) if db_path else _DEFAULT_DB
    out_csv = Path(output_csv) if output_csv else _DEFAULT_OUTPUT
    headshots_dir = Path(headshots_dir) if headshots_dir else _DEFAULT_HEADSHOTS_DIR

    players = collect_players_with_external_ids(db)
    results: List[Dict[str, str]] = []
    seen_image_urls: set[str] = set()
    successful_writes = 0

    for p in players:
        pid = (p.get("player_id") or "").strip()
        espn_id = (p.get("espn_player_id") or "").strip()
        if not pid or not espn_id:
            continue

        image_url = build_espn_headshot_url(espn_id)
        if image_url in seen_image_urls:
            logger.warning("Duplicate image URL %s for player_id=%s; skipping", image_url, pid)
            continue

        dest_jpg = headshots_dir / f"{pid}.jpg"
        headshot_url_path = build_headshot_path(pid)

        wrote = False
        if dry_run:
            logger.info("[dry-run] would write %s <- %s", dest_jpg, image_url)
            wrote = True
        elif dest_jpg.exists() and not overwrite:
            logger.info("Skip existing (use --overwrite): %s", dest_jpg)
            wrote = True
        else:
            png_bytes = _download_bytes(image_url, timeout=timeout)
            time.sleep(delay)
            if png_bytes:
                jpg_bytes = _png_to_jpeg(png_bytes)
                dest_jpg.parent.mkdir(parents=True, exist_ok=True)
                dest_jpg.write_bytes(jpg_bytes)
                wrote = True
                successful_writes += 1

        if wrote:
            seen_image_urls.add(image_url)
            results.append(
                {
                    "player_id": pid,
                    "player_name": p.get("player_name") or "",
                    "team": p.get("team") or "",
                    "position": p.get("position") or "",
                    "espn_player_id": espn_id,
                    "source_image_url": image_url,
                    "headshot_url": headshot_url_path,
                }
            )

        if validation_mode:
            logger.info("Validation mode processed one player; stopping.")
            break
        if limit is not None and successful_writes >= limit:
            logger.info("Reached --limit=%s successful downloads; stopping.", limit)
            break

    results.sort(key=lambda r: r["player_id"])

    if not dry_run:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "player_id",
            "player_name",
            "team",
            "position",
            "espn_player_id",
            "source_image_url",
            "headshot_url",
        ]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in results:
                w.writerow(row)
        logger.info("Saved %s mapping rows to %s", len(results), out_csv.absolute())
    else:
        logger.info("[dry-run] would save %s mapping rows to %s", len(results), out_csv)

    logger.info("Player headshots log file: %s", _LOG_PATH)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download headshots to data/headshots/{player_id}.jpg using players.espn_player_id."
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write JPGs or CSV.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing JPGs.")
    parser.add_argument("--delay", type=float, default=0.05, help="Seconds between HTTP requests.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout for downloads.")
    parser.add_argument("--limit", type=int, default=0, help="Max successful image downloads (0 = no cap).")
    parser.add_argument("--validation-mode", action="store_true", help="Process exactly one player and stop.")
    parser.add_argument("--db", type=Path, default=None, help="Path to nfl_stats.db")
    parser.add_argument("--csv", type=Path, default=None, help="Output CSV path")
    parser.add_argument("--headshots-dir", type=Path, default=None, help="Directory for {player_id}.jpg files")

    args = parser.parse_args(argv)

    lim = args.limit if args.limit > 0 else None

    try:
        run_pipeline(
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            delay=max(0.0, args.delay),
            timeout=max(1, args.timeout),
            limit=lim,
            db_path=args.db,
            output_csv=args.csv,
            headshots_dir=args.headshots_dir,
            validation_mode=args.validation_mode,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
