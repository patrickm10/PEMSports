"""
Pytest configuration and shared fixtures.

Fixtures provide:
- A FastAPI test client (no real server needed)
- Isolated test assertions without network dependencies
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure src/ is importable
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

@pytest.fixture(scope="module")
def client():
    """FastAPI test client — shares a single app instance per test module."""
    from backend.main import app

    with TestClient(app) as c:
        yield c
