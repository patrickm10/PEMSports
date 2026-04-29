"""
Entrypoint wrapper for the ID-based headshot pipeline.

Canonical implementation lives in:
  src/pipelines/player_headshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


from pipelines.player_headshots import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())