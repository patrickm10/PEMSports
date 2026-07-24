---
name: pem-data-coverage
description: >-
  Diagnose and fix PEM Sports season/position/week coverage gaps from parquet
  through DuckDB bake, FastAPI /seasons, and frontend filters. Use when users
  only see 2025, historical years return empty seasonal rankings, /seasons is
  truncated, or production bake may be missing years.
---

# PEM Sports data coverage

## Grounded contract

| Dimension | Values |
|-----------|--------|
| Years | 2020–2025 (`EXPECTED_YEARS` in `scripts/validate_db_completeness.py`) |
| Weeks | 1–18 |
| Positions | QB, RB, WR, TE, K, DST |
| Serving files | `data/rankings/{POS}_{weekly\|seasonal}.parquet` (git-tracked) |

## Known failure mode (2026-07-23)

**Committed seasonal parquet for QB/RB/WR/TE/K was 2025-only.** Weekly retained history. `/seasons` read seasonal-only → UI year dropdown showed `[2025]`. Weekly API still had 2020–2025 but was unreachable via normal year selection.

Overwrite vector: `scripts/convert_seasonal.py` writing from partial CSV sets **without** year coverage assert (now guarded — verify before trusting).

## Triage order (do not skip)

1. Compare **git HEAD** vs worktree seasonal years (temp `git show HEAD:data/rankings/QB_seasonal.parquet`).  
2. `python scripts/validate_db_completeness.py --mode both`  
3. Live or local: `GET /api/v1/rankings/{pos}/seasons` vs `GET ...?year=2024` vs `.../weekly?year=2024&week=1`  
4. Confirm frontend uses `/seasons` / `/weeks` only (no hardcoded YEARS arrays).  
5. Production: only fixed after **commit + Render bake**; local DB alone does not update live.

## Automation checklist

```powershell
$env:PYTHONPATH="src"
python scripts/build_players_dimension.py
python scripts/bake_db.py
python scripts/validate_db_completeness.py --mode both
python -m pytest tests/test_coverage_contract.py tests/test_convert_seasonal_guard.py -v --tb=short
```

Render `buildCommand` must include validate after bake (`render.yaml`).

## Classification labels

| Label | Meaning |
|-------|---------|
| PIPE | Missing/truncated parquet generation or convert overwrite |
| BAKE | Parquet OK, DuckDB incomplete |
| API | Query/metadata loss (e.g. seasons seasonal-only) |
| FE | Metadata OK, UI not exposing |
| SRC | Not in source (do not invent) |

## Related

- Skill: `.cursor/skills/parquet-duckdb-parity-triage/SKILL.md`
- Playbook: `swarm/coverage_overhaul_orchestration.md`
- Audits: `docs/agent_context/DATA_COVERAGE_AUDIT.md`
