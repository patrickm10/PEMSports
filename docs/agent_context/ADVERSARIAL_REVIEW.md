# Adversarial Review — Coverage + UI Overhaul

**Date:** 2026-07-24  
**Scope:** Post-implementation review of data coverage fixes and UI filter overhaul  
**Reviewers:** Lead + [Adversarial coverage review](89828d0b-5a25-4696-a5c3-b3785aa4624d) + [Adversarial UI review](015ea955-60eb-427e-816b-827e38bad2fc)

---

## Verdict

**Local / git:** PASS (parquet restored, validate+pytest, FE build).  
**Production Critical:** still **OPEN** until Render successfully deploys `f0265fd` (3.11 f-string fix) and serves multi-year seasonal.  
**UI Critical/High:** logged as **post-deploy backlog** (presentation contract debt); not blocking the coverage ship.

---

## Reviewer 1 — Coverage / pipeline ([89828d0b](89828d0b-5a25-4696-a5c3-b3785aa4624d))

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| F1 / C1 | **Critical** | Live QB `/seasons` still `[2025]`; seasonal `year=2024` → `[]` after push of `106b561` | **Open** — Render bake never completed (SyntaxError on validate); fix in `f0265fd` **ahead of origin** — must push |
| C7 | **Critical** | Render `SyntaxError`: f-string backslash in `validate_db_completeness.py:266` on Python 3.11 | **Fixed** in `f0265fd` — extract path before f-string |
| F2 | — | Local validate `--mode both` PASS; full year matrix in worktree DB | **PASS** |
| F3 / C2 | High | `query_seasons` union can list years missing from seasonal | **Accepted/mitigated** — validate fails deploy on seasonal gaps; UI empty states; optional follow-up: fixture test for union |
| F4 / C5 | High→Med | `convert_seasonal` skips DST | **Accepted** — DST not produced by that script; DST seasonal already complete |
| F5 / C4 | High→Med | Weekly API tests only week=1 / subset of years | **Accepted** — full matrix owned by `validate_db_completeness`; optional spot-check weeks 9/18 later |
| F6 | Medium | Local-only parquet without commit | **Closed** for this ship — parquet on `main` at `106b561` |
| F7 | Medium | No unit test for seasons union fallback | **Deferred** |
| F8 | Medium | Validate discovers files; does not assert all six positions if file deleted | **Deferred** |

---

## Reviewer 2 — UI / architecture ([015ea955](015ea955-60eb-427e-816b-827e38bad2fc))

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| C1 | Critical | `VirtualizedGrid` re-sorts `filteredData` (contract) | **Backlog** — post-coverage; align grid to API order or amend contract |
| C2 | Critical | Ranking charts aggregate/sort outside `contract.ts` / normalizers | **Backlog** — route via normalizers or amend presentation contract |
| H1 | High | Top-10 chart by metric vs table by `rank` | **Backlog** — align default sorts |
| H2 | High | `StatsSummary` client reduce (known debt) | **Accepted** — pre-existing; presentation-contract debt |
| H3 | High | Mobile cards hardcode PPR/YDS/TD | **Backlog** — drive from `resolvedMetric` |
| H4 | High | Reset week from stale `availableWeeks` for prior year | **Backlog** — reset week after year settles |
| H5 | High | Dashboard facet empty in season while Top 10 renders | **Backlog** — coherent dashboard gating |
| H6 | High | Desktop row click not keyboard-accessible; no `aria-sort` | **Backlog** |
| U1–U2 | High | Dock eslint / vitest+vite build | **Fixed** earlier this session |
| M1–M7 / L* | Med/Low | Hardcoded positions, density dupes, a11y polish, naming | **Deferred** |

---

## Live probes (2026-07-24, pre-`f0265fd` deploy)

| Check | Result |
|-------|--------|
| Push `106b561` / `a031228` to `origin/main` | Succeeded |
| Vercel `a031228` | **READY** — `pemsports.com` title `PEM Sports` |
| Render API root / health | Still legacy branding (`NFL Stats Analyzer API`) |
| `GET .../QB/seasons` | `[2025]` |
| `GET .../QB?year=2024&limit=3` | `[]` |
| `GET .../DST/seasons` | Full 2020–2025 |

---

## Validation evidence (local)

| Check | Result |
|-------|--------|
| `validate_db_completeness --mode both` | PASS |
| `pytest` | 168 passed |
| Frontend lint / vitest / build | PASS (0 lint errors) |
| `validate_db_completeness.py` py_compile after f-string fix | PASS |

---

## Next actions (ordered)

1. `git push origin HEAD` — ship `f0265fd` so Render rebuild can pass validate.
2. Confirm live `/QB/seasons` = 2020–2025 and seasonal `year=2024` non-empty.
3. UI backlog from Reviewer 2 (C1/C2, H1–H6) — start after production coverage is green.
