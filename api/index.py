from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable so `backend.main` resolves in Vercel's Python runtime.
_SRC = (Path(__file__).resolve().parent.parent / "src").resolve()
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Vercel expects an ASGI app named `app`.
from backend.main import app  # noqa: E402

