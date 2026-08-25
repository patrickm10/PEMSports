"""Name normalization shared by Draft Lab player resolution."""

from __future__ import annotations

import re
import unicodedata


def normalize_name(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = [p for p in s.split(" ") if p not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    return " ".join(parts).strip()
