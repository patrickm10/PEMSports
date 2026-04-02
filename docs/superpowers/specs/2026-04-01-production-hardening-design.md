# Production Hardening — Design Spec

## Problem

NFLStatsAnalyzer is a functional prototype targeting public deployment. The system has 10 verified issues that make it unsuitable for real users:

- 2 API routes crash on first request (broken imports)
- CORS is `allow_origins=["*"]` despite computing a restricted list
- Debug `print()` statements in production hot paths
- Zero automated test coverage
- Weekly query does a full table scan then filters in Python
- 27+ orphaned debug/temp files at project root
- Stale pipeline (`get_full_season_rankings.py`) writes to wrong directory
- Pydantic models exist but are bypassed
- Dockerfile has fragile module path configuration
- Duplicate scraper logic between two files

## Goal

Transform the system from "crashes in production" to "deployable with confidence" — without adding new features. This is Phase 1 of a 3-phase production readiness plan:

1. **Phase 1 (this spec)**: Repository cleanup & hardening
2. **Phase 2**: Wire Postgres, auth schema, login
3. **Phase 3**: Scale queries, CI/CD, 5-10x data growth

## Scope — Phase 1 Only

### 1. Fix Broken Backend Imports

**Files**: `src/backend/api/ranking_routes.py`, `src/backend/services/ranking_service.py`

Two routes reference functions that are never imported:
- `get_player_impact` (line 147 in ranking_routes.py) — calls service function that references `query_player_impact_metrics` without importing it
- `get_defense_stats` (line 158 in ranking_routes.py) — calls service function that references `query_team_defense_stats` without importing it

**Fix**: Add missing imports from `backend.data.query_engine` into `ranking_service.py`. The query engine already has these functions (`query_player_impact_metrics` and `query_team_defense_stats`).

### 2. Lock CORS

**File**: `src/backend/main.py`

Line 69 uses `allow_origins=["*"]` while lines 60-65 compute a proper `_allowed_origins` list from env vars. The computed list is never used.

**Fix**: Replace `["*"]` with `_allowed_origins`. Set `allow_credentials=True` (required for future auth cookies).

### 3. Remove Debug Print Statements

**File**: `src/backend/services/ranking_service.py`

6 `print()` calls on lines 47, 51, 57, 92, 96, 104. These are noisy in production and leak internal cache key formats.

**Fix**: Remove all `print()` calls. The existing `logger.debug()` calls below them already provide structured logging.

### 4. Optimize Weekly Query (Eliminate Full Table Scan)

**File**: `src/backend/data/query_engine.py`

`query_weekly_rankings()` (line 298) does `SELECT * FROM view` then filters year/week in Python pandas. At 5-10x data growth this becomes a performance problem.

**Fix**: Push WHERE clauses into DuckDB SQL. Build the SQL conditionally based on provided year/week parameters. Remove the Python-side pandas filtering.

### 5. Clean Root Artifacts

**Root directory** contains 15+ files that are debug/temp artifacts not part of the application:

Delete: `alignment_results.txt`, `backend_err.log`, `backend_trace.log`, `check_years.py`, `cols.txt`, `column_audit.txt`, `data_diagnose.log`, `debug_cmc.json`, `debug_cmc.py`, `final_audit.py`, `report.txt`, `schema_validator.py`, `state_handoff.md`, `test_api.json`, `test_rich_schedule.py`, `verification_report.txt`, `verify_distinct_schemas.py`, `verify_enriched_data.py`, `verify_weekly_pipeline.py`, `walkthrough.md`

### 6. Scaffold Test Infrastructure

**New files**: `tests/conftest.py`, `tests/test_query_engine.py`, `tests/test_ranking_routes.py`

Add pytest infrastructure with:
- A `conftest.py` that configures test fixtures (FastAPI test client, test DuckDB connection)
- Unit tests for the query engine (verify views register, rankings return expected shape)
- Integration tests for API routes (verify HTTP status codes, response shapes, error handling)
- Verify the 2 previously-broken routes now return valid responses

### 7. Fix Dockerfile PYTHONPATH

**File**: `Dockerfile`

Add `ENV PYTHONPATH=/app/src` so the `src.backend.main:app` module path resolves correctly regardless of working directory.

## Out of Scope

- Postgres wiring (Phase 2)
- Auth/login (Phase 2)
- CI/CD pipeline (Phase 3)
- New data sources (Phase 3)
- Frontend changes beyond V1 cleanup (already done)
- Removing `get_full_season_rankings.py` — it's stale but harmless; address in Phase 2

## Verification Plan

1. `pytest tests/` — all tests pass
2. Backend starts without errors: `uvicorn backend.main:app`
3. All 8 API endpoints return valid responses (no 500s)
4. CORS is locked — requests from unlisted origins are rejected
5. No `print()` statements in service layer
6. Root directory has no orphaned debug files
