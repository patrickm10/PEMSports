"""
One-time migration utility: convert legacy headshots stored by (team, player_name)
into the canonical ID-based model.

Legacy layout (example):
  data/headshots/{team}/{player_name}.jpg

Target layout:
  data/headshots/{player_id}.jpg

This script is intentionally strict:
- Logs unmatched files
- Logs duplicate matches
- Fails if *any* ambiguity exists (determinism requirement)
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger("migrate_headshots")


@dataclass(frozen=True)
class MigrationReport:
    total_files: int
    migrated: int
    unmatched: int
    ambiguous: int
    already_present: int = 0


def _iter_legacy_files(old_dir: Path) -> Iterable[Path]:
    # One-time migration is allowed to walk the legacy directory tree.
    yield from old_dir.rglob("*.jpg")


def _extract_team_and_name(path: Path, old_dir: Path) -> tuple[str, str] | None:
    """
    Parse: old_dir/{team}/{player_name}.jpg
    """
    try:
        rel = path.relative_to(old_dir)
    except Exception:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    team = parts[0]
    name = Path(parts[-1]).stem
    return team, name


def _rows(roster_df: Any) -> list[dict[str, Any]]:
    """
    Normalize roster_df into list-of-dicts.
    Supports:
      - list[dict]
      - pandas/polars-ish objects that expose to_dict('records') / iterrows() / rows()
    """
    if roster_df is None:
        return []
    if isinstance(roster_df, list):
        out: list[dict[str, Any]] = []
        for item in roster_df:
            if not isinstance(item, dict):
                raise TypeError("roster_df list entries must be dicts.")
            out.append(dict(item))
        return out
    if hasattr(roster_df, "to_dict"):
        try:
            return list(roster_df.to_dict("records"))  # type: ignore[arg-type]
        except Exception:
            pass
    if hasattr(roster_df, "iterrows"):
        out = []
        for _, r in roster_df.iterrows():  # type: ignore[attr-defined]
            out.append(dict(r))
        return out
    if hasattr(roster_df, "rows"):
        try:
            return [dict(r) for r in roster_df.rows(named=True)]  # type: ignore[attr-defined]
        except Exception:
            pass
    raise TypeError("Unsupported roster_df type; expected list[dict] or pandas/polars-like DataFrame.")


def migrate_headshots(old_dir: str, new_dir: str, roster_df) -> MigrationReport:
    """
    Migrate legacy team/name headshots into canonical {player_id}.jpg files.

    Matching contract:
    - roster_df must contain: player_id, team, player_name
    - Match is exact on (team, player_name) after `.strip()`

    Determinism contract:
    - If multiple roster rows match a single legacy file → error
    """
    old_root = Path(old_dir).resolve()
    new_root = Path(new_dir).resolve()
    if old_root == new_root:
        raise ValueError(
            "old_dir and new_dir resolve to the same path. "
            "Use a separate legacy directory (e.g. data/headshots_legacy) "
            "and write canonical assets to data/headshots/{player_id}.jpg."
        )
    new_root.mkdir(parents=True, exist_ok=True)

    roster_rows = _rows(roster_df)
    index: dict[tuple[str, str], list[str]] = {}
    for r in roster_rows:
        pid = str(r.get("player_id") or "").strip()
        team = str(r.get("team") or "").strip()
        name = str(r.get("player_name") or "").strip()
        if not pid or not team or not name:
            continue
        index.setdefault((team, name), []).append(pid)

    total = 0
    migrated = 0
    already_present = 0
    unmatched: list[str] = []
    ambiguous: list[str] = []

    for f in _iter_legacy_files(old_root):
        total += 1
        parsed = _extract_team_and_name(f, old_root)
        if not parsed:
            unmatched.append(str(f))
            continue
        team, name = parsed
        hits = index.get((team.strip(), name.strip()))
        if not hits:
            unmatched.append(str(f))
            continue
        if len(hits) != 1:
            ambiguous.append(f"{f} -> {hits}")
            continue

        pid = hits[0]
        dest = new_root / f"{pid}.jpg"
        if dest.exists():
            # Idempotent: destination already keyed by player_id — leave legacy file in place.
            already_present += 1
            continue
        shutil.move(str(f), str(dest))
        migrated += 1

    for u in unmatched[:50]:
        logger.warning("Unmatched headshot: %s", u)
    if len(unmatched) > 50:
        logger.warning("Unmatched headshots: %d more...", len(unmatched) - 50)

    for a in ambiguous[:50]:
        logger.error("Ambiguous headshot match: %s", a)
    if len(ambiguous) > 50:
        logger.error("Ambiguous headshots: %d more...", len(ambiguous) - 50)

    if ambiguous:
        raise RuntimeError(
            f"Headshot migration ambiguity: {len(ambiguous)} files had duplicate matches or conflicts."
        )

    return MigrationReport(
        total_files=total,
        migrated=migrated,
        unmatched=len(unmatched),
        ambiguous=len(ambiguous),
        already_present=already_present,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _name_slug(value: str) -> str:
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def _slug_to_team_abbr() -> dict[str, str]:
    """Map franchise slug → lowercase team abbr used by legacy headshot folders."""
    import sys

    src = str(_repo_root() / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from pipelines.constants import TEAM_MAP  # noqa: WPS433

    out: dict[str, str] = {}
    for abbr, slug in TEAM_MAP.items():
        # Prefer the first (canonical) abbreviation for each franchise slug.
        out.setdefault(slug, abbr.lower())
    return out


def _load_players_roster(players_csv: Path) -> list[dict[str, Any]]:
    import csv

    if not players_csv.exists():
        raise FileNotFoundError(f"Missing players CSV: {players_csv}")

    slug_to_abbr = _slug_to_team_abbr()
    rows: list[dict[str, Any]] = []
    with open(players_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid = str(r.get("player_id") or "").strip()
            name = str(r.get("player_name") or "").strip()
            team_slug = str(r.get("team") or "").strip()
            if not pid or not name:
                continue
            team = slug_to_abbr.get(team_slug, team_slug.lower())
            rows.append(
                {
                    "player_id": pid,
                    "legacy_player_id": str(r.get("legacy_player_id") or "").strip(),
                    # Legacy files are team-abbr dirs + snake_case filenames.
                    "team": team,
                    "player_name": _name_slug(name),
                }
            )
    return rows


def prepare_legacy_dir(*, headshots_dir: Path, legacy_dir: Path) -> int:
    """
    Move nested team folders (e.g. data/headshots/ari/*.jpg) into legacy_dir.

    Flat {player_id}.jpg files stay in headshots_dir.
    """
    legacy_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    for child in sorted(headshots_dir.iterdir()):
        if not child.is_dir():
            continue
        dest = legacy_dir / child.name
        if dest.exists():
            # Merge files into existing team folder.
            dest.mkdir(parents=True, exist_ok=True)
            for f in child.glob("*.jpg"):
                target = dest / f.name
                if target.exists():
                    continue
                shutil.move(str(f), str(target))
                moved += 1
            # Remove empty source dir when possible.
            try:
                child.rmdir()
            except OSError:
                pass
        else:
            shutil.move(str(child), str(dest))
            moved += len(list(dest.glob("*.jpg")))
    return moved


def materialize_from_assets(
    *,
    players_csv: Path,
    assets_dir: Path,
    headshots_dir: Path,
    overwrite: bool = False,
) -> int:
    """
    Convert assets/players/{legacy_player_id}.png → data/headshots/{player_id}.jpg.
    """
    import csv

    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Pillow is required to convert PNG assets to JPG.") from exc

    if not assets_dir.exists():
        logger.warning("Assets dir missing; skip: %s", assets_dir)
        return 0

    headshots_dir.mkdir(parents=True, exist_ok=True)
    wrote = 0
    with open(players_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pid = str(r.get("player_id") or "").strip()
            lid = str(r.get("legacy_player_id") or "").strip()
            if not pid or not lid:
                continue
            src = assets_dir / f"{lid}.png"
            if not src.exists():
                continue
            dest = headshots_dir / f"{pid}.jpg"
            if dest.exists() and not overwrite:
                continue
            with Image.open(src) as im:
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(dest, format="JPEG", quality=90, optimize=True, progressive=True)
            wrote += 1
    logger.info("Materialized %d headshots from %s", wrote, assets_dir)
    return wrote


def main(argv: list[str] | None = None) -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root = _repo_root()
    p = argparse.ArgumentParser(
        description=(
            "Migrate legacy team/name headshots to data/headshots/{player_id}.jpg "
            "and optionally materialize from assets/players PNGs."
        )
    )
    p.add_argument(
        "--headshots-dir",
        type=Path,
        default=root / "data" / "headshots",
        help="Canonical headshots directory (flat {player_id}.jpg)",
    )
    p.add_argument(
        "--legacy-dir",
        type=Path,
        default=root / "data" / "headshots_legacy",
        help="Directory for nested team/name legacy JPGs",
    )
    p.add_argument(
        "--players-csv",
        type=Path,
        default=root / "data" / "players.csv",
        help="Players dimension CSV",
    )
    p.add_argument(
        "--prepare-legacy",
        action="store_true",
        help="Move nested team folders from --headshots-dir into --legacy-dir first",
    )
    p.add_argument(
        "--from-assets",
        action="store_true",
        help="Also convert assets/players/{legacy_player_id}.png → {player_id}.jpg",
    )
    p.add_argument(
        "--assets-dir",
        type=Path,
        default=root / "assets" / "players",
        help="Legacy PNG assets directory",
    )
    p.add_argument(
        "--overwrite-assets",
        action="store_true",
        help="Overwrite existing JPGs when materializing from assets",
    )
    p.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip team/name migration (assets-only mode)",
    )
    args = p.parse_args(argv)

    try:
        if args.prepare_legacy:
            n = prepare_legacy_dir(headshots_dir=args.headshots_dir, legacy_dir=args.legacy_dir)
            logger.info("Prepared legacy dir with %d nested JPG moves into %s", n, args.legacy_dir)

        if args.from_assets:
            materialize_from_assets(
                players_csv=args.players_csv,
                assets_dir=args.assets_dir,
                headshots_dir=args.headshots_dir,
                overwrite=args.overwrite_assets,
            )

        if not args.skip_migrate:
            if not args.legacy_dir.exists():
                raise FileNotFoundError(
                    f"Legacy dir missing: {args.legacy_dir}. "
                    "Pass --prepare-legacy if nested folders still live under data/headshots/."
                )
            roster = _load_players_roster(args.players_csv)
            report = migrate_headshots(str(args.legacy_dir), str(args.headshots_dir), roster)
            logger.info(
                "Migration complete: total=%d migrated=%d already_present=%d unmatched=%d ambiguous=%d",
                report.total_files,
                report.migrated,
                report.already_present,
                report.unmatched,
                report.ambiguous,
            )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

