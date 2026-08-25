"""
Pytest configuration and shared fixtures.

Fixtures provide:
- A FastAPI test client (no real server needed)
- Isolated test assertions without network dependencies
"""
import json
import sys
import time
from pathlib import Path

# #region agent log
def _agent_dbg(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": "d2039e",
            "runId": "post-fix-pandas",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        log_path = Path(__file__).resolve().parent.parent / "debug-d2039e.log"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception:
        pass


_httpx_ok = False
_httpx_err = None
try:
    import httpx  # noqa: F401

    _httpx_ok = True
except Exception as exc:  # noqa: BLE001
    _httpx_err = f"{type(exc).__name__}: {exc}"

_agent_dbg(
    "H1",
    "tests/conftest.py:httpx-import",
    "httpx import probe before TestClient",
    {"httpx_ok": _httpx_ok, "httpx_err": _httpx_err, "python": sys.version.split()[0]},
)

try:
    import fastapi
    import starlette
    from importlib.metadata import version as _pkg_version

    _agent_dbg(
        "H3",
        "tests/conftest.py:pkg-versions",
        "resolved web-stack versions",
        {
            "fastapi": getattr(fastapi, "__version__", None),
            "starlette": getattr(starlette, "__version__", None),
            "fastapi_meta": _pkg_version("fastapi"),
            "starlette_meta": _pkg_version("starlette"),
        },
    )
except Exception as exc:  # noqa: BLE001
    _agent_dbg(
        "H3",
        "tests/conftest.py:pkg-versions",
        "failed to read package versions",
        {"err": f"{type(exc).__name__}: {exc}"},
    )

_req_txt = Path(__file__).resolve().parent.parent / "requirements.txt"
_req_has_httpx = False
try:
    _req_has_httpx = "httpx" in _req_txt.read_text(encoding="utf-8").lower()
except Exception:
    pass
_agent_dbg(
    "H2",
    "tests/conftest.py:requirements",
    "requirements.txt httpx declaration",
    {"requirements_exists": _req_txt.exists(), "httpx_declared": _req_has_httpx},
)

_pandas_ok = False
_pandas_err = None
_pyarrow_ok = False
_pyarrow_err = None
try:
    import pandas as _pandas  # noqa: F401

    _pandas_ok = True
except Exception as exc:  # noqa: BLE001
    _pandas_err = f"{type(exc).__name__}: {exc}"
try:
    import pyarrow as _pyarrow  # noqa: F401

    _pyarrow_ok = True
except Exception as exc:  # noqa: BLE001
    _pyarrow_err = f"{type(exc).__name__}: {exc}"
_req_pandas_declared = False
try:
    _req_pandas_declared = any(
        (not line.strip().startswith("#")) and "pandas==" in line
        for line in _req_txt.read_text(encoding="utf-8").lower().splitlines()
    )
except Exception:
    pass
_agent_dbg(
    "H6",
    "tests/conftest.py:pandas-import",
    "pandas/pyarrow probe before collecting pipeline tests",
    {
        "pandas_ok": _pandas_ok,
        "pandas_err": _pandas_err,
        "pyarrow_ok": _pyarrow_ok,
        "pyarrow_err": _pyarrow_err,
        "pandas_declared_in_requirements": _req_pandas_declared,
    },
)
# #endregion

import pytest
from fastapi.testclient import TestClient

# Ensure src/ is importable
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI test client — shares a single app instance per test module."""
    with TestClient(app) as c:
        yield c
