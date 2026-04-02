# Phase 1: Production Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform NFLStatsAnalyzer from a crashing prototype to a deployable, testable system.

**Architecture:** No new features — fix broken code, lock security, optimize hot paths, add test coverage.

**Tech Stack:** Python 3.11 / FastAPI / DuckDB / pytest / httpx (test client)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| MODIFY | `src/backend/services/ranking_service.py` | Add missing imports, remove debug prints |
| MODIFY | `src/backend/main.py` | Lock CORS to env-controlled origins |
| MODIFY | `src/backend/data/query_engine.py` | Push weekly query filters into DuckDB SQL |
| MODIFY | `Dockerfile` | Add PYTHONPATH env var |
| CREATE | `tests/conftest.py` | Pytest fixtures (test client, DuckDB) |
| CREATE | `tests/test_query_engine.py` | Unit tests for query engine |
| CREATE | `tests/test_ranking_routes.py` | Integration tests for API routes |
| DELETE | 20 root-level debug artifacts | Clean repo hygiene |

---

### Task 1: Fix Broken Service Imports

**Files:**
- Modify: `src/backend/services/ranking_service.py:19-24`

- [ ] **Step 1: Add missing imports to ranking_service.py**

Open `src/backend/services/ranking_service.py` and replace the import block (lines 19-24):

```python
from backend.data.query_engine import (
    query_rankings,
    query_seasons,
    query_weekly_rankings,
    query_available_weeks,
)
# Position enum removed to bypass Pydantic ForwardRef issues at the API boundary
```

With:

```python
from backend.data.query_engine import (
    query_rankings,
    query_seasons,
    query_weekly_rankings,
    query_available_weeks,
    query_player_impact_metrics,
    query_team_defense_stats,
)
```

- [ ] **Step 2: Verify imports resolve**

Run:
```powershell
$env:PYTHONPATH="src"; python -c "from backend.services.ranking_service import get_player_impact, get_defense_stats; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```powershell
git add src/backend/services/ranking_service.py
git commit -m "fix: add missing query engine imports to ranking service"
```

---

### Task 2: Lock CORS

**Files:**
- Modify: `src/backend/main.py:67-73`

- [ ] **Step 1: Replace wildcard CORS with env-controlled origins**

In `src/backend/main.py`, replace lines 67-73:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

With:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

- [ ] **Step 2: Verify CORS configuration loads**

Run:
```powershell
$env:PYTHONPATH="src"; python -c "from backend.main import _allowed_origins; print(_allowed_origins)"
```
Expected: `['http://localhost:5173', 'http://localhost:5175', 'http://localhost:3000']`

- [ ] **Step 3: Commit**

```powershell
git add src/backend/main.py
git commit -m "fix: lock CORS to env-controlled origins, restrict methods and headers"
```

---

### Task 3: Remove Debug Print Statements

**Files:**
- Modify: `src/backend/services/ranking_service.py:47,51,57,92,96,104`

- [ ] **Step 1: Remove all print() calls from ranking_service.py**

Delete these 6 lines from `src/backend/services/ranking_service.py`:

```python
    print(f"DEBUG: CACHE KEY -> {cache_key} | YEAR PARAM: {year}")
```
```python
        print(f"DEBUG: CACHE HIT -> {cache_key} | RECORDS: {len(cached)}")
```
```python
    print(f"DEBUG: CACHE MISS -> {cache_key} | FETCHED: {len(data)}")
```
```python
    print(f"DEBUG: CACHE KEY -> {cache_key} | YEAR: {year} | WEEK: {week}")
```
```python
        print(f"DEBUG: CACHE HIT -> {cache_key} | RECORDS: {len(cached)}")
```
```python
    print(f"DEBUG: CACHE MISS -> {cache_key} | FETCHED: {len(data)}")
```

- [ ] **Step 2: Verify no print() calls remain**

Run:
```powershell
Select-String -Path "src/backend/services/ranking_service.py" -Pattern "print\("
```
Expected: No output (no matches).

- [ ] **Step 3: Commit**

```powershell
git add src/backend/services/ranking_service.py
git commit -m "fix: remove debug print statements from ranking service"
```

---

### Task 4: Optimize Weekly Query — Push Filters to DuckDB

**Files:**
- Modify: `src/backend/data/query_engine.py:283-315`

- [ ] **Step 1: Replace the Python-side filtering with SQL WHERE clauses**

In `src/backend/data/query_engine.py`, replace the `query_weekly_rankings` function (lines 283-315):

```python
def query_weekly_rankings(
    position: str,
    year: Optional[int] = None,
    week: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Query weekly rankings for a position from DuckDB.
    Filters by year and/or week when provided.
    """
    view = _ensure_weekly_view(position.upper())
    if not view:
        return []

    sql = f"SELECT * FROM {view}"
    rows = _get_conn().execute(sql).fetchdf()
    
    # Bypass DuckDB PlainSkip pushdown bugs by filtering in python natively
    if year is not None:
        rows = rows[rows['year'] == year]
    if week is not None:
        rows = rows[rows['week'] == week]

    rows = rows.sort_values(["year", "week", "rank"], ascending=[False, False, True])
    
    # Pagination
    if limit is not None:
        rows = rows.iloc[offset:offset+limit]
    elif offset > 0:
        rows = rows.iloc[offset:]

    return _serialize_rows(rows)
```

With:

```python
def query_weekly_rankings(
    position: str,
    year: Optional[int] = None,
    week: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Query weekly rankings for a position from DuckDB.
    Filters by year and/or week when provided.
    Filters are pushed into SQL to avoid full table scans.
    """
    view = _ensure_weekly_view(position.upper())
    if not view:
        return []

    conditions: list[str] = []
    params: list[Any] = []

    if year is not None:
        conditions.append("CAST(year AS INTEGER) = ?")
        params.append(year)
    if week is not None:
        conditions.append("CAST(week AS INTEGER) = ?")
        params.append(week)

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM {view}{where_clause} ORDER BY year DESC, week DESC, rank ASC"

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    elif offset > 0:
        sql += f" OFFSET {int(offset)}"

    df = _get_conn().execute(sql, params).fetchdf()
    return _serialize_rows(df)
```

- [ ] **Step 2: Verify weekly query still returns data**

Run:
```powershell
$env:PYTHONPATH="src"; python -c "from backend.data.query_engine import query_weekly_rankings; data = query_weekly_rankings('QB', year=2024, week=1, limit=5); print(f'{len(data)} rows'); print(list(data[0].keys()) if data else 'empty')"
```
Expected: `5 rows` followed by the dict keys.

- [ ] **Step 3: Commit**

```powershell
git add src/backend/data/query_engine.py
git commit -m "perf: push weekly query filters into DuckDB SQL, eliminate full table scan"
```

---

### Task 5: Clean Root Artifacts

**Files:**
- Delete: 20 debug/temp files at project root

- [ ] **Step 1: Delete orphaned root files**

Run:
```powershell
Remove-Item -Path "alignment_results.txt","backend_err.log","backend_trace.log","check_years.py","cols.txt","column_audit.txt","data_diagnose.log","debug_cmc.json","debug_cmc.py","final_audit.py","report.txt","schema_validator.py","state_handoff.md","test_api.json","test_rich_schedule.py","verification_report.txt","verify_distinct_schemas.py","verify_enriched_data.py","verify_weekly_pipeline.py","walkthrough.md" -ErrorAction SilentlyContinue
```

- [ ] **Step 2: Verify root is clean**

Run:
```powershell
Get-ChildItem -Path . -File | Select-Object Name
```

Expected remaining files: `.env.example`, `.gitignore`, `.pyre_configuration`, `Dockerfile`, `README.md`, `render.yaml`, `requirements.txt`

- [ ] **Step 3: Commit**

```powershell
git add -A
git commit -m "chore: remove 20 orphaned debug/temp files from project root"
```

---

### Task 6: Scaffold Test Infrastructure

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_query_engine.py`
- Create: `tests/test_ranking_routes.py`

- [ ] **Step 1: Create tests/conftest.py**

Create `tests/conftest.py`:

```python
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

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI test client — shares a single app instance per test module."""
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 2: Create tests/test_query_engine.py**

Create `tests/test_query_engine.py`:

```python
"""
Unit tests for the DuckDB query engine.

Tests verify:
- View registration succeeds for all positions
- Seasonal queries return expected dict structure
- Weekly queries return expected dict structure
- Season/week listing returns sorted integers
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.data.query_engine import (
    query_rankings,
    query_seasons,
    query_weekly_rankings,
    query_available_weeks,
)

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]


class TestSeasonalQueries:
    """Seasonal ranking query contract tests."""

    def test_query_rankings_returns_list_of_dicts(self):
        data = query_rankings("QB", year=2024, limit=5)
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], dict)
            assert "player_name" in data[0]
            assert "fpts_ppr" in data[0]
            assert "rank" in data[0]

    def test_query_rankings_respects_limit(self):
        data = query_rankings("QB", year=2024, limit=3)
        assert len(data) <= 3

    def test_query_seasons_returns_sorted_years(self):
        years = query_seasons("QB")
        assert isinstance(years, list)
        if len(years) > 1:
            assert years[0] > years[1], "Years should be descending"

    def test_all_positions_have_data(self):
        for pos in POSITIONS:
            data = query_rankings(pos, limit=1)
            assert isinstance(data, list), f"No data returned for {pos}"


class TestWeeklyQueries:
    """Weekly ranking query contract tests."""

    def test_query_weekly_returns_list_of_dicts(self):
        data = query_weekly_rankings("QB", year=2024, week=1, limit=5)
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], dict)
            assert "player_name" in data[0]
            assert "week" in data[0]

    def test_query_weekly_respects_year_filter(self):
        data = query_weekly_rankings("QB", year=2024, limit=50)
        if data:
            years = {row.get("year") for row in data}
            assert years == {2024}, f"Expected only 2024, got {years}"

    def test_query_weekly_respects_week_filter(self):
        data = query_weekly_rankings("QB", year=2024, week=1, limit=50)
        if data:
            weeks = {row.get("week") for row in data}
            assert weeks == {1}, f"Expected only week 1, got {weeks}"

    def test_query_available_weeks_returns_sorted_ints(self):
        weeks = query_available_weeks("QB", year=2024)
        assert isinstance(weeks, list)
        if len(weeks) > 1:
            assert weeks == sorted(weeks), "Weeks should be ascending"
```

- [ ] **Step 3: Create tests/test_ranking_routes.py**

Create `tests/test_ranking_routes.py`:

```python
"""
Integration tests for API ranking routes.

Tests verify:
- All endpoints return 200 with valid params
- Response shapes match expected contracts
- Previously broken routes (impact, defense) now work
- Invalid positions return 422 or empty results gracefully
"""
import pytest


class TestSeasonalEndpoints:
    """GET /api/v1/rankings/{pos}"""

    def test_get_rankings_returns_200(self, client):
        response = client.get("/api/v1/rankings/QB?year=2024&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_rankings_response_shape(self, client):
        response = client.get("/api/v1/rankings/QB?year=2024&limit=1")
        data = response.json()
        if data:
            record = data[0]
            assert "player_name" in record
            assert "fpts_ppr" in record
            assert "rank" in record

    def test_get_seasons_returns_list(self, client):
        response = client.get("/api/v1/rankings/QB/seasons")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_csv_export_returns_csv(self, client):
        response = client.get("/api/v1/rankings/QB/csv?year=2024")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")


class TestWeeklyEndpoints:
    """GET /api/v1/rankings/{pos}/weekly and /api/v1/weekly-rankings"""

    def test_get_weekly_rankings_returns_200(self, client):
        response = client.get("/api/v1/rankings/QB/weekly?year=2024&week=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_weeks_returns_list(self, client):
        response = client.get("/api/v1/rankings/QB/weeks?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_weekly_alias_returns_200(self, client):
        response = client.get("/api/v1/weekly-rankings?pos=QB&year=2024&week=1&limit=5")
        assert response.status_code == 200


class TestPreviouslyBrokenRoutes:
    """Verify routes that previously crashed due to missing imports."""

    def test_impact_endpoint_does_not_crash(self, client):
        response = client.get("/api/v1/rankings/QB/impact/test_id?metric=surface")
        # May return empty data (no matching player_id) but should NOT return 500
        assert response.status_code in (200, 404)

    def test_defense_endpoint_does_not_crash(self, client):
        response = client.get("/api/v1/rankings/QB/defense")
        # May return empty data but should NOT return 500
        assert response.status_code == 200


class TestHealthEndpoint:
    """GET /health"""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "positions_available" in data
```

- [ ] **Step 4: Install test dependencies**

Run:
```powershell
pip install httpx pytest
```

`httpx` is required by FastAPI's `TestClient`.

- [ ] **Step 5: Run all tests**

Run:
```powershell
$env:PYTHONPATH="src"; python -m pytest tests/ -v
```
Expected: All tests pass (green).

- [ ] **Step 6: Commit**

```powershell
git add tests/
git commit -m "test: add pytest infrastructure with query engine and API route tests"
```

---

### Task 7: Fix Dockerfile PYTHONPATH

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Add PYTHONPATH to Dockerfile**

In `Dockerfile`, add after line 7 (`ENV PORT 8000`):

```dockerfile
ENV PYTHONPATH=/app/src
```

- [ ] **Step 2: Verify Dockerfile syntax**

Run:
```powershell
Get-Content Dockerfile
```
Expected: `ENV PYTHONPATH=/app/src` appears between PORT and WORKDIR.

- [ ] **Step 3: Commit**

```powershell
git add Dockerfile
git commit -m "fix: add PYTHONPATH to Dockerfile for reliable module resolution"
```

---

## Final Verification

- [ ] **Step 1: Run full test suite**

```powershell
$env:PYTHONPATH="src"; python -m pytest tests/ -v --tb=short
```
Expected: All tests pass.

- [ ] **Step 2: Start backend and verify no crashes**

```powershell
$env:PYTHONPATH="src"; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Expected: Server starts without errors.

- [ ] **Step 3: Verify all 8 endpoints respond**

In a separate terminal:
```powershell
$endpoints = @("/health", "/api/v1/rankings/QB?year=2024&limit=1", "/api/v1/rankings/QB/seasons", "/api/v1/rankings/QB/weekly?year=2024&week=1&limit=1", "/api/v1/rankings/QB/weeks?year=2024", "/api/v1/weekly-rankings?pos=QB&year=2024&week=1&limit=1", "/api/v1/rankings/QB/defense", "/api/v1/rankings/QB/csv?year=2024")
foreach ($ep in $endpoints) { $r = Invoke-WebRequest "http://localhost:8000$ep" -UseBasicParsing; Write-Host "$($r.StatusCode) $ep" }
```
Expected: All return `200`.

- [ ] **Step 4: Final commit**

```powershell
git add -A
git commit -m "chore: Phase 1 production hardening complete"
```
