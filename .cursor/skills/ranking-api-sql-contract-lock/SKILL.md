---
name: ranking-api-sql-contract-lock
description: >-
  Keeps changes to FastAPI rankings endpoints aligned with ranking_service,
  query_engine SQL, HTTP status semantics, and stable JSON contracts. Use when
  editing src/backend/api/ranking_routes.py, src/backend/services/ranking_service.py,
  or rankings-related SQL in query_engine.py, or when debugging 422 vs 404 vs 500
  on /rankings routes.
---

# Ranking API SQL contract lock (NFLStatsAnalyzer)

## When this applies

User changes or debugs anything under `src/backend/api/ranking_routes.py`, `src/backend/services/ranking_service.py`, or SQL/strings in `src/backend/data/query_engine.py` used for rankings; or reports 422 vs 404 vs 500 confusion on `/rankings/...`.

**Example prompt:** "Add a `team` filter to GET `/rankings/{pos}/weekly` — what do I touch and what breaks clients?"

## Execution rules (follow in order)

1. Order the boundary: **route** (`ranking_routes.py`: path/query validation, year `2018–2030`, week `1–18`, `limit`/`offset` caps) → **service** (`ranking_service.py`) → **`run_query` / SQL** (`query_engine.py`).
2. Invalid `pos` → **422** per route module; do not remap to 400.
3. Before code: write the **filter contract**: parameter name, type, allowed range, default, and whether it changes SQL `WHERE` only or also pagination.
4. Any new query parameter must define interaction with `year`, `week`, `limit`, `offset` (explicit AND semantics).
5. Do not wrap route handlers in `except Exception`; domain errors surface as `NFLStatsException` subclasses for the global handler in `main.py`.
6. Response shape: additive fields OK, removals breaking (per route docstring); call out breaking removals explicitly.
7. After intent is clear, give at most **one** minimal SQL fragment **or** **one** service signature change — not both unless the user asked for full stack.
8. Do not dump full files; cite at most four symbols (file + function) total.

## Required output shape

```text
BOUNDARY: route | service | query_engine — which layer changes
HTTP: expected status codes for invalid pos | OOR year/week | no rows | missing table | db missing — table ≤5 rows
CONTRACT: bullets (params + defaults + SQL predicate mapping)
DELTA: single sentence — what to edit where
RISK: breaking | non-breaking — one word + one clause
```

## Before vs after

- **Before:** "Add `team` in FastAPI and filter in pandas after the query so it is easier."
- **After:**

```text
BOUNDARY: route + service + query_engine — all three if SQL filters
HTTP: invalid pos → 422; year/week OOR → 422; no rows → 200 + []; missing table → 404; db missing → 503
CONTRACT: team optional str; AND team = normalize_team_abbr(team) in SQL when present; limit/offset unchanged order
DELTA: add Query on api_get_weekly_rankings, thread through get_weekly_rankings, extend WHERE in query_engine only
RISK: non-breaking — additive query param and JSON fields only
```
