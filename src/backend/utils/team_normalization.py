from __future__ import annotations

from typing import Optional

from constants import TEAM_MAP


def _slugify_team_name(raw: str) -> str:
    # Mirrors the pipeline's slug rules but stays TEAM_MAP-driven.
    return (
        str(raw)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace("'", "")
    )


def _build_slug_to_canonical_abbr() -> dict[str, str]:
    """
    Invert TEAM_MAP (abbr -> slug) to (slug -> canonical abbr).

    TEAM_MAP may contain historical/alias abbreviations (e.g. JAC, OAK, STL).
    We pick the first abbreviation encountered for each slug, so insertion order
    in TEAM_MAP defines the canonical abbreviation.
    """
    inv: dict[str, str] = {}
    for abbr, slug in TEAM_MAP.items():
        if slug not in inv:
            inv[slug] = abbr
    return inv


_SLUG_TO_CANON_ABBR = _build_slug_to_canonical_abbr()


def normalize_team_abbr(raw: Optional[str]) -> Optional[str]:
    """
    Normalize a raw opponent/team value into a standardized team abbreviation.

    Rules:
    - Case-normalize safely via upper()
    - If the value is already a known abbreviation (a key in TEAM_MAP), return its upper() form
    - If the value looks like a slug or full name, slugify and map slug->canonical abbr
    - If not found, return the original value unchanged
    """
    if raw is None:
        return None

    s = str(raw).strip()
    if not s:
        return raw

    up = s.upper()
    if up in TEAM_MAP:
        return up

    slug = _slugify_team_name(s)
    return _SLUG_TO_CANON_ABBR.get(slug, raw)

