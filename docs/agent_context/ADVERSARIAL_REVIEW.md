# Adversarial Review — Coverage + UI Overhaul

**Date:** 2026-07-24  
**Scope:** Post-implementation review of data coverage fixes and UI filter overhaul  
**Reviewers:** Lead + two read-only adversarial agents (coverage, UI)

---

## Verdict

**PASS for Critical** after dispositions below.  
**High findings** either fixed in-session or accepted with documented mitigations.

---

## Reviewer 1 — Coverage / pipeline layers

| ID | Severity | Finding | Evidence | Disposition |
|----|----------|---------|----------|-------------|
| C1 | **Critical** | Production still 2025-only until restored seasonal parquet is **committed and baked on Render** | Live 2026-07-23 `/QB/seasons` → `[2025]`; git HEAD seasonal skill positions 2025-only | **Resolve via deploy** — commit parquet + push; Render `buildCommand` now includes validate |
| C2 | High | `query_seasons` unions weekly years → UI can list a year whose **seasonal** table is empty | `query_engine.py:184-215` | **Accepted/mitigated** — UI empty state explains empty combo; `validate_db_completeness` fails deploy if seasonal years missing; seasonal parquet restored |
| C3 | High | Partial CSV convert could wipe multi-year seasonal | Pre-fix `convert_seasonal.py` | **Fixed** — expected-year assert + `tests/test_convert_seasonal_guard.py` |
| C4 | Medium | Weekly row tests sample week=1 / subset of years, not every week×year | `tests/test_coverage_contract.py` | **Accepted** — weeks metadata asserts 1–18 for sampled years; full year×week matrix is validate script’s job |
| C5 | Medium | `convert_seasonal` does not cover DST | `convert_seasonal.py` positions list | **Accepted** — DST seasonal already complete 2020–2025; DST uses different ingest path |
| C6 | Low | 2025 weekly row inflation (~2–3×) | Parquet row counts | **Deferred** — quality issue, not year-selection loss |

---

## Reviewer 2 — UI / architecture / a11y

| ID | Severity | Finding | Evidence | Disposition |
|----|----------|---------|----------|-------------|
| U1 | High | ResponsiveDock `setState` in `useEffect` failed eslint | `ResponsiveDock.tsx` (pre-fix) | **Fixed** — close nav via event handlers; lint clean (0 errors) |
| U2 | High | Vitest import path / vite+vitest config type clash broke build | `filterState.test.ts`, `vite.config.ts` | **Fixed** — `./filterState` import; separate `vitest.config.ts` |
| U3 | Medium | StatsSummary still averages metrics client-side | `StatsSummary.tsx` (known contract debt) | **Accepted** — pre-existing; not introduced by this overhaul; tracked in presentation contract |
| U4 | Medium | Charts re-sort top-10 by metric; grid sorts by rank | `chartOptions.ts` vs `VirtualizedGrid` | **Accepted** — same `filteredData` source; different presentation order is intentional |
| U5 | Medium | Grid headers lack `aria-sort` | `VirtualizedGrid.tsx` | **Deferred** — not Critical for coverage ship |
| U6 | Low | `MAX_YEARS = 6` in analytics normalizers | `normalizers.ts:175` | **OK** — player analytics chart window, not rankings year filter |
| U7 | Low | Preserved `nflstats:search` localStorage key | `searchStore.ts` | **OK** — external contract |

---

## Validation evidence (2026-07-24)

| Check | Result |
|-------|--------|
| `validate_db_completeness --mode both` | PASS (prior session; worktree) |
| `pytest` | 168 passed (prior session) |
| Frontend lint | 0 errors (5 pre-existing warnings) |
| Frontend vitest | 7 passed |
| Frontend `npm run build` | PASS |

---

## Residual production risk

Until Wave 4 deploy completes: live API remains on old bake (2025-only seasonal skill positions; legacy branding). Local PASS ≠ production PASS.
