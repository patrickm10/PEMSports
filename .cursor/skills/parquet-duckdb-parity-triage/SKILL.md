---
name: parquet-duckdb-parity-triage
description: >-
  Triages mismatches between data/rankings parquet, data/nfl_stats.db (DuckDB),
  and the FastAPI serving path. Use when the user reports wrong row counts,
  missing weeks or years, empty API/UI while parquet exists, enrichment vs
  rankings drift, or asks to compare parquet to the baked database.
---

# Parquet–DuckDB parity triage (NFLStatsAnalyzer)

## When this applies

User reports any of: wrong row counts, missing weeks/years, UI/API empty while files exist, parquet has data but API does not, enrichment vs rankings mismatch, or debugging `data/nfl_stats.db` vs `data/rankings/*.parquet`.

**Example prompt:** "QB weekly 2023 W7 shows nothing in the app but I see rows in the parquet — is the DB stale?"

## Execution rules (follow in order)

1. State the three-layer chain in one line: `data/rankings/{POS}_*.parquet` → `scripts/bake_db.py` → `src/backend/data/query_engine.py` → `NFL_STATS_DB_PATH` (default repo `data/nfl_stats.db`).
2. Do not propose new product SQL until steps 5–6 are satisfied.
3. Run `scripts/validate_db_completeness.py` with `--mode both`, or the narrowest mode the symptom implies (`parquet` | `duckdb` | `both` only).
4. If output references missing pairs or `duckdb_less_complete_than_parquet`, classify as **bake drift** (fix is rebake, not API).
5. If validator is clean, apply `query_engine.py` contract: `[]` = successful zero rows; distinguish from `DatabaseUnavailableError`, `TableMissingError`, `QueryEngineError` per file docstring.
6. If DB path ambiguity: state explicit `NFL_STATS_DB_PATH` at runtime vs path in validator output; do not assume match without both values.
7. Maximum three hypotheses; each maps to one artifact path or one script outcome.
8. Do not expand into unrelated pipelines (`enrichment.py`, scrapers) unless the user names them or validator output references those tables.

## Required output shape

```text
LAYER_CHECK: parquet | duckdb | api — one line
VALIDATOR: command + mode + pass|fail + top finding (≤3 bullets)
ROOT_CAUSE: bake_drift | path_mismatch | query_filter | empty_legitimate | unknown — one label
NEXT_ACTION: single concrete step (one command or one file edit target)
```

## Before vs after

- **Before:** "Maybe the API is broken or DuckDB is weird; try rewriting the query and check the frontend cache."
- **After:**

```text
LAYER_CHECK: duckdb behind parquet for QB_weekly — bake layer
VALIDATOR: python scripts/validate_db_completeness.py --mode both — fail — duckdb missing (2023,7) for QB_weekly
ROOT_CAUSE: bake_drift
NEXT_ACTION: rerun scripts/bake_db.py for QB (or full bake); confirm NFL_STATS_DB_PATH matches the same data/nfl_stats.db the API loads
```
