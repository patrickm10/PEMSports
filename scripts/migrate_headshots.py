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
    Supports pandas/polars-ish objects that expose:
      - to_dict('records')
      - iterrows()
      - rows() (polars)
    """
    if roster_df is None:
        return []
    if hasattr(roster_df, "to_dict"):
        try:
            return list(roster_df.to_dict("records"))  # type: ignore[arg-type]
        except Exception:
            pass
    if hasattr(roster_df, "iterrows"):
        out: list[dict[str, Any]] = []
        for _, r in roster_df.iterrows():  # type: ignore[attr-defined]
            out.append(dict(r))
        return out
    if hasattr(roster_df, "rows"):
        try:
            return [dict(r) for r in roster_df.rows(named=True)]  # type: ignore[attr-defined]
        except Exception:
            pass
    raise TypeError("Unsupported roster_df type; expected pandas/polars-like DataFrame.")


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
            # Deterministic overwrite behavior is caller-owned; we treat this as ambiguity.
            ambiguous.append(f"{f} -> dest_exists {dest}")
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
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(
        "Import and call migrate_headshots(old_dir, new_dir, roster_df) from your notebook/script."
    )

