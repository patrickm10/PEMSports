# Coverage + UI Overhaul — Reasoning Log

**Date:** 2026-07-23  
**Status:** STOPPED for handoff (FE validation + deploy incomplete)

## Discovery conclusion

Earliest loss = **committed seasonal parquet** (QB/RB/WR/TE/K = 2025 only), not frontend year hardcoding and not API `year` default.

## Implemented in worktree (uncommitted)

| Change | Why |
|--------|-----|
| Restored seasonal parquet (worktree) | Restore source of truth for bake |
| `query_seasons` union seasonal+weekly | Defensive metadata if seasonal regresses |
| `convert_seasonal.py` expected-year guard | Prevent 2025-only overwrite |
| `render.yaml` + validate `--mode both` | Fail deploy on coverage loss |
| `tests/test_coverage_contract.py` | Regression protection |
| UI ControlBar/App/ResponsiveDock/filterState | Global filters, a11y, errors, mobile nav |
| Vitest `filterState.test.ts` | Filter persistence/reset contract |

## Verification

- Backend chain: **PASS** (bake + validate both + pytest 168)
- Frontend lint/test/build: **NOT RUN to completion** (aborted)

## Remaining for next session

1. FE lint → test → build  
2. Adversarial reviewers + `ADVERSARIAL_REVIEW.md` + `UI_IMPLEMENTATION_SUMMARY.md`  
3. Commit parquet + code; push; Render/Vercel redeploy  
4. Live probe `/seasons` + `year=2024` seasonal non-empty  

## Architect compliance

- `filteredData` preserved; DuckDB rankings; Neon auth-only; no URL renames.
