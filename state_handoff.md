# Session Handoff: NFL Analytics Data Hardening

## Current Objective
Enforce a **Zero-Transformation Passthrough** from DuckDB/Parquet to Frontend for 2025 seasonal stats (QB/RB/WR/TE/K).

## Status Summary
- **Storage Layer [SUCCESS]:** `data/nfl_stats.db` is correctly hydrated. Standalone audit verified Josh Allen's seasonal total is **385.10 FPTS** (Sum of 16 weeks). All 5 positions have 2025 data: QB (544 rows / 65 players), RB (544 / 91), WR (850 / 139), TE (850 / 112), K (544 / 46).
- **V3 Parquet Layer [PRESENT]:** Weekly-level mirrors exist at `data/v3/qb_stats.parquet`, `rb_stats.parquet`, etc. These are full DuckDB table exports (not pre-aggregated).
- **Code Changes [PARTIAL — WRONG TARGET]:** Router mount order and passthrough refactor applied to `backend/main.py` and `backend/api/v1/rankings.py`. These are **NOT the files the active server uses**.
- **The Blocker [ACTIVE — ROOT CAUSE IDENTIFIED]:** See below.

## ROOT CAUSE (Confirmed)

### Dual Backend Architecture
There are **TWO separate backend applications** in this repository:

| Component | Path | Purpose |
|-----------|------|---------|
| **Legacy Backend** | `backend/main.py` | Simple FastAPI, DuckDB-backed, imports from `backend/services/position_helper.py` |
| **Production Backend** | `src/backend/main.py` | Full FastAPI with rate limiting, auth, Postgres, caching, imports from `src/backend/services/ranking_service.py` → `src/backend/data/query_engine.py` |

### Which Server Is Active on Port 8000
**`src/backend/main.py`** is the one answering requests. Confirmed by:
- Root endpoint returns `{"message": "NFL Stats Analyzer API", "version": "1.0.0", "docs": "/docs"}` — matches `src/backend/main.py` line 129.
- `backend/main.py` returns a different message: `"NFL Stats Analyzer API is running. Visit /docs for documentation."`.

### Why the API Returns Empty
The active query engine (`src/backend/data/query_engine.py`) resolves data from:
```
data/rankings/{POS}_seasonal.parquet  (for seasonal data)
data/rankings/{POS}_weekly.parquet    (for weekly data)
```
**`data/rankings/` DOES NOT EXIST.** It falls back to `data_local/raw_scrapes/` CSV files, and if those don't match, returns `FileNotFoundError` → empty `[]`.

The data that DOES exist is:
- `data/nfl_stats.db` (DuckDB persistent database — used by legacy `backend/`)
- `data/v3/*.parquet` (weekly mirrors of DuckDB tables — NOT referenced by either backend)

### Data Flow Summary
```
Frontend → /api/v1/rankings/qb?year=2025
         → src/backend/api/ranking_routes.py → ranking_service.py → query_engine.py
         → _resolve_data_path("QB", "historical")
         → Looks for data/rankings/QB_seasonal.parquet → NOT FOUND
         → Looks for data_local/raw_scrapes/QB_*.csv → NOT FOUND
         → Returns [] (empty)
```

## Changes Already Made (To Wrong Target)
1. `backend/main.py` — Router mounting order swapped (V1 first)
2. `backend/api/v1/rankings.py` — Normalization removed, `df.to_dicts()` passthrough, HTTP 500 on empty

These changes are **correct in logic** but target the **wrong backend**. The active server uses `src/backend/`.

## DuckDB Schema (Verified)
Column names for each position table in `data/nfl_stats.db`:

**QB:** Rank, Player, CMP, Pass_Att, PCT, Pass_Yds, Y/A, Pass_TD, INT, SACKS, Rush Att, Rush Yds, Rush TD, FL, G, FPTS, FPTS/G, ROST, team_abbr, team_name, year, week, Score, stadium_name, indoor_outdoor, surface_type, elevation, year_opened, city, state, latitude, longitude, Team Name

**RB:** Rank, Player, ATT, Rush Yds, Y/A, LG, 20+, Rush TD, REC, TGT, Rec Yds, Y/R, Rec TD, FL, G, FPTS, FPTS/G, ROST, team_abbr, team_name, year, week, Score, stadium_name, indoor_outdoor, surface_type, elevation, year_opened, city, state, latitude, longitude, Team Name

**WR/TE:** Rank, Player, REC, TGT, Rec Yds, Y/R, LG, 20+, Rec TD, ATT, Rec Yds_duplicated_0, Rec TD_duplicated_0, FL, G, FPTS, FPTS/G, ROST, team_abbr, team_name, year, week, Score, (stadiums...), Team Name

**K:** Rank, Player, Team Name, Score, FPTS, FG, FGA, PCT, LG, 1-19, 20-29, 30-39, 40-49, 50+, XPT, XPA, (stadiums...), G, ROST, week, year

## Next Steps for Next Session
1. **DECISION POINT — pick ONE approach:**
   - **(A) Fix the active backend (`src/backend/`):** Create `data/rankings/` with correctly named Parquet files (symlinks or copies from `data/v3/` or DuckDB exports). Then apply the passthrough + HTTP 500 changes to `src/backend/api/ranking_routes.py` and `src/backend/data/query_engine.py`.
   - **(B) Switch the server to the legacy backend (`backend/`):** Start uvicorn with the correct `backend.main:app` confirming it binds to port 8000 and no stale processes interfere. The passthrough changes are already applied there. But this backend doesn't support rate limiting, auth, or caching.
   - **(C) Unify both backends:** Consolidate into a single backend. Highest effort but cleanest long-term.

2. **If Approach (A):** The query engine expects `data/rankings/QB_seasonal.parquet`. Create this directory and export/link the Parquet files with the correct naming convention.

3. **If Approach (B):** Ensure all Python/Node processes are killed. Start with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`. Verify root endpoint returns the correct message.

## Critical Files
### Active Backend (the one answering on :8000)
- `src/backend/main.py` (Route registration, app creation)
- `src/backend/api/ranking_routes.py` (Rankings API handlers)
- `src/backend/services/ranking_service.py` (Service + cache layer)
- `src/backend/data/query_engine.py` (DuckDB views, data resolution — **THIS IS WHERE THE BUG LIVES**)

### Legacy Backend (already has passthrough edits)
- `backend/main.py` (Route registration — V1 first)
- `backend/api/v1/rankings.py` (Zero-transformation passthrough)
- `backend/services/position_helper.py` (GROUP BY aggregation — DO NOT MODIFY)

### Data Assets
- `data/nfl_stats.db` — DuckDB with correct 2025 weekly data
- `data/v3/*.parquet` — Weekly Parquet mirrors
- `data/rankings/` — **DOES NOT EXIST** (this is what the active backend looks for)
