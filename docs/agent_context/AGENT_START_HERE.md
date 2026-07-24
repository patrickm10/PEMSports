# AGENT START HERE — PEM Sports

Snapshot date: 2026-07-23. Verify production claims before relying on them.

## Project identity

- Product: **PEM Sports** (formerly NFLStatsPro / NFLStatsAnalyzer)
- API display name: **PEM Sports API** · Slug: `pem-sports` · Code id: `pem_sports` · Domain: `pemsports.com`
- Repo folder and GitHub slug remain `NFLStatsAnalyzer` (external contract — do not rename).
- NFL fantasy analytics: historical rankings (seasonal + weekly, 2020–2025) per position (QB/RB/WR/TE/K/DST).

## Current architecture

```text
FantasyPros scrape (src/pipelines) → data/rankings/*.parquet (git-tracked)
→ scripts/build_players_dimension.py → data/players.csv (gitignored)
→ scripts/bake_db.py → data/nfl_stats.db (DuckDB, gitignored build artifact)
→ FastAPI (src/backend, read-only DuckDB) → React/Vite SPA (frontend/nflstats-pro-ui)
Auth only: Neon Postgres via DATABASE_URL (src/backend/data/postgres.py)
Deploy: backend Render (render.yaml), frontend Vercel (vercel.json) at pemsports.com
```

## Mandatory invariants

1. `filteredData` (App.tsx) is the only presentation contract.
2. `resolvePrimaryMetric` (`frontend/.../src/utils/metrics.ts`) is the only metric-defining layer; the frontend must not compute metrics.
3. Charts must not read table/grid state.
4. Context between layers is structured typed data with explicit nulls.
5. Adjusted and unadjusted metrics are first-class paired columns (NOT yet implemented — see ARCHITECTURE_AUDIT.md before building on this).
6. Every metric is reproducible from pipeline code; never patch parquet or `nfl_stats.db` by hand.
7. DuckDB is the read-only rankings store; Neon Postgres is isolated to transactional features (auth).
8. Presentation code must not bypass the backend analytics contract.

## Correct commands (PowerShell, repo root)

```powershell
$env:PYTHONPATH="src"
python scripts/build_players_dimension.py        # players dimension
python scripts/bake_db.py                        # bake DuckDB from parquet
python scripts/validate_db_completeness.py --mode both
python -m pytest tests/ -v --tb=short
uvicorn backend.main:app --reload --app-dir src  # local API :8000

cd frontend/nflstats-pro-ui
npm ci; if ($LASTEXITCODE -eq 0) { npm run lint }; if ($LASTEXITCODE -eq 0) { npm run test }; if ($LASTEXITCODE -eq 0) { npm run build }; if ($LASTEXITCODE -eq 0) { npm run dev } # UI :5173
```

Coverage regression skill: `.agents/skills/pem-data-coverage/SKILL.md`. Swarm playbook: `swarm/coverage_overhaul_orchestration.md`.
Or chain with `&&` in a shell that supports it.

## Critical paths

- Backend entry: `src/backend/main.py` · SQL: `src/backend/data/query_engine.py` · routes: `src/backend/api/*_routes.py`
- Health: `src/backend/core/health.py` (`GET /health`, always HTTP 200; check body `status`)
- Exceptions: `src/backend/core/exceptions.py` (`PemSportsException`; legacy alias `NFLStatsException`)
- Frontend API base: `frontend/nflstats-pro-ui/src/utils/backendOrigin.ts` (`VITE_API_BASE` → `VITE_API_BASE_URL` → dev localhost)
- Config/env parsing: `src/backend/core/config.py`

## Pipeline entry points

See `PIPELINE_RUNBOOK.md`. Highlights: weekly scrape `src/pipelines/get_weekly_rankings.py`; seasonal scrape `src/pipelines/get_full_season_rankings.py` (NOT run by `src/run_pipelines.py --all` — known gap); bake `scripts/bake_db.py`; validate `scripts/validate_db_completeness.py`.

## Production status (verified 2026-07-23)

- `https://pemsports.com` — **live** (HTTP 200); bundle still pre-rebrand (`NFLStatsPro` / title `nflstats-pro-ui`) until Vercel redeploy.
- `https://nflstats-api.onrender.com` — **up**; CORS OK; branding still `NFL Stats Analyzer API` until Render redeploy of current `main`.
- Data gap: skill-position **seasonal** tables on prod are **2025-only**; weekly 2020–2025 present; DST seasonal complete. Root cause: committed seasonal parquet (see `DATA_COVERAGE_AUDIT.md`, `state_handoff.md`).
- Local worktree has restored seasonal parquet + coverage guards; **not production until commit + Render bake**.

## Active blockers

1. Uncommitted restored `{POS}_seasonal.parquet` + coverage/UI changes must be committed and deployed.
2. Frontend lint/test/build not verified in last session (aborted).
3. Neon Auth provisioned but unused; app uses custom JWT + `users` table.
4. `espn_player_id` empty in players dimension → headshot pipeline can't fetch real ESPN images.

## External contracts (do not rename/break)

`/api/v1/*` routes · `NFL_STATS_DB_PATH` · `data/nfl_stats.db` · Render service `nflstats-api` + its URL · `frontend/nflstats-pro-ui/` path (vercel.json, CI, root package.json) · localStorage key `nflstats:search` · env var names (`VITE_API_BASE`, `ALLOWED_ORIGINS`, `DATABASE_URL`, `JWT_SECRET`, `APP_ENV`) · GitHub slug `patrickm10/NFLStatsAnalyzer` · scraper User-Agent strings. Full list: `BRAND_MIGRATION.md`.

## Deprecated paths

- Root `api/index.py` (legacy Vercel serverless) — excluded by `.vercelignore`; never use for production.
- Root `pipelines/` — deprecated; canonical code is `src/pipelines/`.
- `data/official_rankings/` outputs + `src/pipelines/add_weather_to_nfl_matchups.py` — stale/disconnected paths.
- `frontend/.../eslint_*.txt`, `lint_output.txt` — stale generated lint dumps.

## Required pre-implementation checks

1. Read the relevant Cursor rule/skill (`.cursor/rules/`, `.cursor/skills/`) for the files you touch.
2. Rankings API changes: follow `ranking-api-sql-contract-lock` skill (status semantics 422/404/500/503).
3. Data changes: rebuild via bake + `validate_db_completeness.py --mode both`; never edit the DB directly.
4. Deploy config changes: follow `deploy-config-contract` skill; keep `render.yaml`/`vercel.json`/env names in sync.
5. Before renaming anything with a legacy name, check `BRAND_MIGRATION.md` — it may be a preserved contract.
