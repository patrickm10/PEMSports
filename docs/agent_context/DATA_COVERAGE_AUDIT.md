# Data Coverage Audit — PEM Sports

**Date:** 2026-07-23  
**Scope:** Source → Parquet → players dimension → DuckDB bake → API → frontend filters  
**Method:** Four read-only discovery agents + lead reconciliation; production HTTP probes

---

## Confirmed root cause

**Earliest confirmed loss:** committed seasonal Parquet for QB/RB/WR/TE/K under `data/rankings/` contained **2025 only** (git HEAD). Production Render bake materializes that artifact into `{pos}_seasonal`. `GET /api/v1/rankings/{pos}/seasons` reads seasonal tables only, so the UI year dropdown showed **[2025]**.

| Layer | Finding |
|-------|---------|
| Source / pipeline intent | `get_full_season_rankings.py` and `validate_db_completeness.py` expect **2020–2025** |
| Committed seasonal Parquet (HEAD) | QB/RB/WR/TE/K = **2025 only**; DST = 2020–2025 |
| Worktree seasonal Parquet (pre-fix) | Full **2020–2025** already restored locally (uncommitted) |
| Weekly Parquet (HEAD + worktree) | **2020–2025**, weeks 1–18 for all positions |
| Players dimension | No year filter; not the loss point |
| `bake_db.py` | Pass-through; no year filter |
| Render build | Bakes without `validate_db_completeness.py` |
| API year default | **None** — no silent `year=2025` |
| Frontend year lists | API-driven via `/seasons` — not hardcoded |

**Not the cause:** year selector hardcoding, API `ge/le` bounds rejecting history, or frontend reset forcing 2025.

**Production compounding factors (2026-07-23):**
- Live API root still branded `NFL Stats Analyzer API` (pre-redeploy).
- Live Vercel bundle still shows `NFLStatsPro` / title `nflstats-pro-ui` (pre-redeploy).
- Omitting `year` on seasonal rankings returns newest-first rows (ORDER BY year DESC + limit), which looks like “2025 only” even when multi-year data exists.

---

## Coverage contract (authoritative)

| Dimension | Supported values | Source of truth |
|-----------|------------------|-----------------|
| Season | 2020–2025 inclusive | Pipelines + `EXPECTED_YEARS` in `validate_db_completeness.py` |
| Position | QB, RB, WR, TE, K, DST | `bake_db.POSITIONS` |
| Week | 1–18 inclusive | `EXPECTED_WEEKS` / weekly pipeline |
| Seasonal rows | One seasonal table per position | `{POS}_seasonal.parquet` → `{pos}_seasonal` |
| Weekly rows | One weekly table per position | `{POS}_weekly.parquet` → `{pos}_weekly` |

Frontend filter options **must** come from:
- `GET /api/v1/rankings/{pos}/seasons`
- `GET /api/v1/rankings/{pos}/weeks?year=`

No hardcoded season/position/week option arrays for rankings filters.

---

## Coverage matrix (2026-07-23)

Status legend: **OK** available & working · **EXP** available but not exposed · **PIPE** missing in pipeline gen · **BAKE** missing in bake · **API** missing in query · **FE** missing only in frontend · **SRC** not in source

### Seasonal (skill positions — git HEAD before correction)

| Season | Pos | Source | Parquet | DuckDB (prod) | API rows | Frontend | Status |
|--------|-----|--------|---------|---------------|----------|----------|--------|
| 2020–2024 | QB/RB/WR/TE/K | Present in worktree restore | **Missing in HEAD** | Empty | `200 []` | Not in `/seasons` | **PIPE** (committed artifact) |
| 2025 | QB/RB/WR/TE/K | Present | Present | Present | Non-empty | Exposed | **OK** |
| 2020–2025 | DST | Present | Present | Present | Non-empty | Exposed | **OK** |

### Weekly (all positions — production + HEAD)

| Season | Pos | Weeks | Parquet | DuckDB (prod) | API | Frontend via year from seasonal | Status |
|--------|-----|-------|---------|---------------|-----|----------------------------------|--------|
| 2020–2025 | All 6 | 1–18 | Present | Present | Non-empty | **Blocked** when `/seasons` = [2025] | **EXP** (data OK, UI year list truncated) |

### After correction (local worktree + bake)

| Season | Pos | Seasonal | Weekly | `/seasons` | Status |
|--------|-----|----------|--------|------------|--------|
| 2020–2025 | All 6 | Rows present | Rows present | Full DESC list | **OK** |

---

## Production probes (2026-07-23)

| Request | Status | Shape / note | Conclusion |
|---------|--------|--------------|------------|
| `GET https://pemsports.com/` | 200 | title `nflstats-pro-ui` | UI live; branding stale |
| `GET https://www.pemsports.com/` | 200 | same bundle | www OK |
| `GET https://nflstats-api.onrender.com/` | 200 | `NFL Stats Analyzer API` | API live; branding stale |
| `GET .../health` | 200 | `service: nfl-stats-analyzer` | Healthy; old build |
| `GET .../QB/seasons` | 200 | `[2025]` | Seasonal metadata truncated |
| `GET .../DST/seasons` | 200 | `[2025..2020]` | DST seasonal complete |
| `GET .../QB?year=2024&limit=3` | 200 | `[]` | Seasonal history missing on prod |
| `GET .../QB/weekly?year=2024&week=1&limit=3` | 200 | 3 rows | Weekly history present |
| Positions × years matrix | — | Seasonal empty 2020–24 for skill pos; weekly OK | Confirms seasonal bake gap |

---

## Ingestion gaps (not invented)

No evidence of seasons outside 2020–2025 in serving Parquet. Pipeline year lists stop at 2025. Pre-2020 data is an **ingestion gap**, not a bake/API bug.

Known secondary quality issue: 2025 weekly row density is ~2–3× prior years (possible scrape concat without dedup). Does not block year selection.

---

## Corrections applied (lead)

1. Retain restored `{POS}_seasonal.parquet` (2020–2025) for QB/RB/WR/TE/K.
2. `query_seasons` unions distinct years from seasonal **and** weekly tables (defensive exposure).
3. Harden `scripts/convert_seasonal.py` with expected-year assert.
4. Render `buildCommand` runs `validate_db_completeness.py --mode both` after bake.
5. Automated API coverage tests for years × positions × weeks metadata.
6. UI consumes API metadata only; adds reset, coverage feedback, error/empty states.

---

## Classification cheat-sheet for future regressions

| Symptom | Likely stage |
|---------|--------------|
| Parquet missing years | PIPE / convert overwrite |
| Parquet OK, DuckDB missing | BAKE |
| DuckDB OK, `/seasons` truncated | API (seasonal-only query) — mitigated by union |
| `/seasons` full, dropdown empty | FE |
| Dropdown full, table empty | API filter / empty combo vs error handling |
