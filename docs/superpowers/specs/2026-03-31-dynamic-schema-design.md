# Dynamic Schema Extract & Preserve Architecture

## Goal Description
The NFL pipeline currently aggregates positional stats and truncates them to an `EXPECTED_SCHEMA` containing roughly 15 generic columns. This rigidly drops specialized stats like `CMP, ATT, PCT, INT, SACKS` (for QBs) or `DEF TD, SFTY, SPC TD` (for DST) across both weekly and seasonal pipelines.
The system needs to embrace dynamic schema parsing to support every raw output stat extracted from FantasyPros without risking truncation.

## 🔴 Root Cause Analysis
1. **Pipeline Truncation**: `get_weekly_rankings.py` and `src/pipelines/rankings/offensive.py` strictly run `combined_df.select(EXPECTED_SCHEMA)`.
2. **Missing Position Execution**: `get_full_season_rankings.py` is hard-coded to `POSITIONS = ["qb"]` and only manually maps explicit `numeric_cols`.

## Proposed Changes (Approach 1: Dynamic Deductions)

### 1. `src/pipelines/transforms/get_new_nfl_data.py`
- Remove all aggressive mappings and schema truncations that destroy the raw positional data. Keep the dedup `R_` prefix behavior, but preserve all outputs un-filtered.

### 2. `src/pipelines/rankings/offensive.py` (Seasonal Pipeline)
- Remove `EXPECTED_SCHEMA`.
- Replace `combined_df.select(EXPECTED_SCHEMA)` with a dynamic selector that just drops useless garbage columns (`ROST`) and preserves everything else.
- Because Parquet natively supports columnar dynamic writing, no structural overhead is required. `get_new_nfl_data` yields dynamic data, and we write it verbatim to the position's `.parquet`.

### 3. `src/pipelines/get_weekly_rankings.py` (Weekly Pipeline)
- Remove `EXPECTED_SCHEMA`.
- Preserve all dynamic base stats from `get_fantasypros_data`.
- Enforce the explicit enrichment array (`opponent, stadium_name, temp, humidity, wind, elevation`) against the dynamic core data before writing to Parquet. 

### 4. `src/backend/data/query_engine.py` (DuckDB Backend)
- Update `_ensure_seasonal_view` and `_ensure_view` to lazily map columns against Parquet via `SELECT * FROM read_parquet()`. DuckDB will dynamically discover the `CMP`, `ATT`, `DEF TD` columns.

### 5. `src/backend/models/data_models.py` (FastAPI JSON Boundary)
- Remove the strict `BaseModel` attributes explicitly typed for every performance metric. Because different positions have entirely different numeric arrays, replace the strict Pydantic model for stats with `**kwargs` / `Extra.allow` dict models so the JSON serialize implicitly packs all discovered DuckDB keys into the HTTP response.

### 6. React Type Models
- Define an indexed type (`[key: string]: string | number | null`) for the `BaseRanking` interface so TypeScript ceases erroring when novel columns like `CMP` or `SACKS` naturally arrive in the JSON package.

## Verification Plan
1. Re-run `python src/pipelines/get_weekly_rankings.py` and `python src/pipelines/rankings/offensive.py`.
2. Generate Parquet output and perform programmatic assertion asserting that the dynamic positional columns definitively exist in the Parquet files via pyarrow inspection.
