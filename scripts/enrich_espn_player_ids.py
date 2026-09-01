"""
Enrich data/players.csv with espn_player_id from the nflverse players dataset.

Headshot serving still uses a single source of truth: players.espn_player_id →
ESPN CDN (see backend.data.headshot_urls). This script only fills that field.

Match on normalized full name + position (and name-only when unique). The
normalizer is the established name layer — no per-player maps.

Provider order:
  1. nflreadpy.load_players() when installed
  2. HTTP fetch of the nflverse-data players.csv release (requests + polars)

Fail-open: network / payload / import errors log a warning and exit 0 so
Render/Docker bake + rankings still succeed without new ESPN ids.

Usage (repo root):
  $env:PYTHONPATH="src"
  python scripts/enrich_espn_player_ids.py
  python scripts/bake_db.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Optional

import requests

logger = logging.getLogger("enrich_espn_player_ids")

USER_AGENT = "PEMSports-enrich_espn_player_ids/1.0"
NFLVERSE_PLAYERS_CSV = (
    "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize_name(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Drop generational / suffix tokens that often differ across data sources.
    parts = [p for p in s.split(" ") if p not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    return " ".join(parts).strip()


def _espn_id_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value == int(value):
            return str(int(value))
    s = str(value).strip()
    if not s or s.lower() in {"none", "nan", "null"}:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _player_display_name(raw: dict[str, Any]) -> str:
    for key in ("display_name", "full_name", "football_name", "player_name"):
        val = raw.get(key)
        if val is not None and str(val).strip() and str(val).strip().lower() not in {"none", "nan"}:
            return str(val).strip()
    first = str(raw.get("first_name") or "").strip()
    last = str(raw.get("last_name") or "").strip()
    return f"{first} {last}".strip()


def _normalize_position(value: Any) -> str:
    pos = str(value or "").strip().upper()
    if pos in {"DEF", "D/ST"}:
        return "DST"
    return pos


def _uniq(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _build_indexes(
    records: Iterable[dict[str, Any]],
) -> tuple[dict[tuple[str, str], list[str]], dict[str, list[str]]]:
    """Index ESPN ids by (normalized name, position) and by name only.

    Records with a null/empty espn_id are skipped (they cannot produce a CDN URL).
    """
    by_name_pos: dict[tuple[str, str], list[str]] = {}
    by_name: dict[str, list[str]] = {}

    for raw in records:
        if not isinstance(raw, dict):
            continue
        eid = _espn_id_str(raw.get("espn_id") if "espn_id" in raw else raw.get("espn_player_id"))
        if not eid:
            continue
        name = normalize_name(_player_display_name(raw))
        if not name:
            continue
        pos = _normalize_position(raw.get("position"))
        by_name.setdefault(name, []).append(eid)
        if pos:
            by_name_pos.setdefault((name, pos), []).append(eid)

    return {k: _uniq(v) for k, v in by_name_pos.items()}, {k: _uniq(v) for k, v in by_name.items()}


# Back-compat alias used by tests that inject Sleeper-shaped records.
_build_sleeper_indexes = _build_indexes


def _records_from_frame(df: Any) -> list[dict[str, Any]]:
    if hasattr(df, "to_dicts"):
        rows = df.to_dicts()
        if isinstance(rows, list):
            return rows
    if hasattr(df, "to_pandas"):
        return df.to_pandas().to_dict("records")
    raise RuntimeError("Unexpected nflverse players payload (expected a DataFrame).")


def _load_nflverse_players_http(*, timeout: int) -> list[dict[str, Any]]:
    import polars as pl

    resp = requests.get(
        NFLVERSE_PLAYERS_CSV,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()
    df = pl.read_csv(BytesIO(resp.content), infer_schema_length=10000)
    records = df.to_dicts()
    if not records:
        raise RuntimeError("nflverse players.csv was empty.")
    logger.info("Loaded %d nflverse players via HTTP release", len(records))
    return records


def _load_nflverse_players(*, timeout: int) -> list[dict[str, Any]]:
    try:
        import nflreadpy as nfl

        df = nfl.load_players()
        records = _records_from_frame(df)
        if records:
            logger.info("Loaded %d nflverse players via nflreadpy", len(records))
            return records
        logger.info("nflreadpy.load_players() returned no rows; trying HTTP release")
    except Exception as exc:  # noqa: BLE001 - fail over to the same nflverse CSV
        logger.info("nflreadpy load failed (%s); trying nflverse HTTP release", exc)
    return _load_nflverse_players_http(timeout=timeout)


def _resolve_espn_id(
    *,
    name: str,
    pos: str,
    by_name_pos: dict[tuple[str, str], list[str]],
    by_name: dict[str, list[str]],
) -> list[str]:
    hits: list[str] = []
    if name and pos:
        hits = by_name_pos.get((name, pos), [])
    if len(hits) != 1 and name:
        name_hits = by_name.get(name, [])
        if len(name_hits) == 1:
            hits = name_hits
    return hits


def enrich_players_csv(
    *,
    players_csv: Path,
    timeout: int = 60,
    overwrite: bool = False,
    nflverse_players: Optional[list[dict[str, Any]]] = None,
) -> dict[str, int]:
    players_csv = Path(players_csv)
    if not players_csv.exists():
        raise FileNotFoundError(f"Missing players CSV: {players_csv}")

    with open(players_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"No rows in {players_csv}")

    fieldnames = list(rows[0].keys())
    if "espn_player_id" not in fieldnames:
        fieldnames.append("espn_player_id")

    records = (
        nflverse_players
        if nflverse_players is not None
        else _load_nflverse_players(timeout=timeout)
    )
    by_name_pos, by_name = _build_indexes(records)

    matched = 0
    preserved = 0
    ambiguous = 0
    missing = 0

    for row in rows:
        existing = str(row.get("espn_player_id") or "").strip()
        if existing and not overwrite:
            preserved += 1
            continue

        name = normalize_name(row.get("player_name") or "")
        pos = _normalize_position(row.get("position"))
        hits = _resolve_espn_id(name=name, pos=pos, by_name_pos=by_name_pos, by_name=by_name)

        if len(hits) == 1:
            row["espn_player_id"] = hits[0]
            matched += 1
        elif len(hits) > 1:
            ambiguous += 1
            if not existing:
                row["espn_player_id"] = ""
        else:
            missing += 1
            if not existing:
                row["espn_player_id"] = ""

    tmp = players_csv.with_suffix(players_csv.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    tmp.replace(players_csv)

    report = {
        "total": len(rows),
        "matched": matched,
        "preserved": preserved,
        "ambiguous": ambiguous,
        "missing": missing,
    }
    logger.info(
        "ESPN id enrichment: total=%d matched=%d preserved=%d ambiguous=%d missing=%d",
        report["total"],
        report["matched"],
        report["preserved"],
        report["ambiguous"],
        report["missing"],
    )
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Fill players.csv espn_player_id from nflverse players (espn_id)."
    )
    p.add_argument(
        "--players-csv",
        type=Path,
        default=_repo_root() / "data" / "players.csv",
        help="Path to players.csv",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout for nflverse players fetch",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing espn_player_id values when a unique match is found",
    )
    args = p.parse_args()

    try:
        enrich_players_csv(
            players_csv=args.players_csv,
            timeout=max(5, args.timeout),
            overwrite=args.overwrite,
        )
    except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
        # Fail-open: never block bake/rankings/deploy when nflverse is unreachable.
        logger.warning("ESPN id enrichment skipped (fail-open): %s", exc)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
