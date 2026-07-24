# Coverage Overhaul Orchestration

**Mission:** Every season/position/week present in serving Parquet is queryable via API and selectable in UI.  
**Updated:** 2026-07-23  
**Handoff:** [`../state_handoff.md`](../state_handoff.md)

---

## Symptom pattern (do not mis-diagnose)

| Symptom | Likely cause | Not the cause |
|---------|--------------|---------------|
| UI only shows 2025 | `/seasons` from incomplete `{pos}_seasonal` | Hardcoded FE year list |
| Seasonal `year=2024` → `[]` but weekly works | Seasonal parquet / bake gap | API year validator |
| Omit `year` → only 2025 rows | `ORDER BY year DESC` + limit | Silent `default=2025` |

---

## Wave 0 — Discovery (4 parallel read-only agents)

1. **Data:** parquet HEAD vs worktree; bake; validate; convert scripts  
2. **Backend:** ranking_routes / query_engine / seasons SQL / live API probes  
3. **Frontend:** ControlBar / App filter state / filteredData  
4. **Production:** pemsports.com + nflstats-api branding + `/seasons` matrix  

Only lead may edit after reconciliation.

---

## Wave 1 — Fix earliest loss

Order matters:

1. Restore/commit `{POS}_seasonal.parquet` for all skill positions (2020–2025)  
2. Guard `convert_seasonal.py` with `EXPECTED_YEARS`  
3. Optional: `query_seasons` union seasonal+weekly  
4. Render `buildCommand` must run `validate_db_completeness.py --mode both`  
5. Add `tests/test_coverage_contract.py` matrix  

---

## Wave 2 — UI around metadata contract

- Years/weeks **only** from `/seasons` and `/weeks`  
- Global filter bar; reset; row counts; loading/error/empty  
- Keep `filteredData` sole row contract  

---

## Wave 3 — Validate + adversarial

```powershell
$env:PYTHONPATH="src"
python scripts/build_players_dimension.py
python scripts/bake_db.py
python scripts/validate_db_completeness.py --mode both
python -m pytest tests/ -v --tb=short

cd frontend/nflstats-pro-ui
npm ci   # or npm install if lockfile intentionally updated
npm run lint; npm run test; npm run build
```

Then two fresh read-only reviewers (coverage + UI). Resolve Critical/High. Write:

- `docs/agent_context/ADVERSARIAL_REVIEW.md`
- `docs/agent_context/UI_IMPLEMENTATION_SUMMARY.md`

---

## Wave 4 — Production

1. Push committed parquet + code  
2. Confirm Render build log: bake + validate PASS  
3. Vercel redeploy for UI/brand  
4. Probe matrix: every position × `/seasons` + seasonal `year=2024` + weekly sample  

Automation skill: [`.agents/skills/pem-data-coverage/SKILL.md`](../.agents/skills/pem-data-coverage/SKILL.md)
