# NFLStatsAnalyzer / NFLStatsPro

Fantasy rankings analytics: **Polars pipelines** → **Parquet** (`data/rankings/`) → **baked DuckDB** (`data/nfl_stats.db`) → **FastAPI** → **Vite + React** dashboard.

**Python 3.10+** · **Node 20** (see CI) · **DuckDB 1.3.1** · **FastAPI** (pinned in `requirements.txt`)

---

## Architecture

```text
data/rankings/{QB,RB,...}_{weekly|seasonal}.parquet   (git-tracked)
        │
        ▼  scripts/bake_db.py
data/nfl_stats.db                                     (local build artifact, gitignored)
        │
        ▼  src/backend/data/query_engine.py (read-only DuckDB)
FastAPI  src/backend/main.py  /api/v1/rankings/...
        │
        ▼  HTTP + CORS
frontend/nflstats-pro-ui  (Vite, React 19)
```

- **Rankings data:** Parquet on disk → materialized tables in `nfl_stats.db` for stable SQL and low cold-start cost on hosts like Render.
- **Transactional / auth:** PostgreSQL via `psycopg` (`src/backend/data/postgres.py`). In **development**, a missing DB logs a warning and auth features degrade; **staging/production** fail startup if the pool cannot open (`src/backend/core/config.py` policy).
- **ETL:** Primary code lives under **`src/pipelines/`**. A legacy **`pipelines/`** folder at repo root still exists—prefer `src/pipelines/` unless you know you need the root copy.

---

## Setup (local)

### 1. Backend

```powershell
cd <repo-root>
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

- **`PYTHONPATH`:** must include `src` when running modules (e.g. `$env:PYTHONPATH="src"`).
- **Serving database:** create `data/nfl_stats.db` from parquet (required before API tests or rankings queries):

```powershell
$env:PYTHONPATH="src"
python scripts/bake_db.py
```

- **Optional:** `NFL_STATS_DB_PATH` overrides the default path (`data/nfl_stats.db` under repo root, resolved in `query_engine.py`).

Run API (example):

```powershell
$env:PYTHONPATH="src"
uvicorn backend.main:app --reload --app-dir src
```

### 2. Frontend

```powershell
cd frontend/nflstats-pro-ui
npm ci
npm run dev
```

Point the UI at your API base URL and ensure **`ALLOWED_ORIGINS`** on the server lists your Vite origin (defaults in `main.py` include `http://localhost:5173`).

### 3. Convenience (Windows)

`scripts/manage_services.py` starts/stops local FastAPI + Vite; it is **Windows-only** as written.

---

## Testing and data checks

```powershell
$env:PYTHONPATH="src"
pytest tests/ -v --tb=short
python scripts/validate_db_completeness.py --mode parquet
```

CI runs pytest and **parquet-mode** completeness validation (`.github/workflows/ci-backend.yml`). It does **not** currently bake `nfl_stats.db` in the workflow—you need a local bake (or your deploy pipeline) for DuckDB-backed tests to match production.

---

## Limitations

| Topic | Detail |
|--------|--------|
| **`nfl_stats.db`** | Gitignored. Fresh clones have no API database until you run `bake_db.py`. |
| **CI vs serving layer** | GitHub Actions validates **parquet** completeness; **parquet ↔ baked DuckDB** parity is a separate manual or deploy-time concern unless you add a bake + `--mode both` step. |
| **Postgres** | Optional in development; production/staging expect a real `DATABASE_URL` and strict config. |
| **Duplicate pipeline roots** | Prefer `src/pipelines/`; root `pipelines/` may confuse imports and docs. |
| **DuckDB / SQL edge cases** | Historical non-QB weekly paths hit DuckDB optimizer limits when scanning raw parquet through certain window patterns; **bake** + served tables is the supported mitigation (see `bake_db.py` header). |

---

## Roadmap (short)

- [ ] CI: bake `nfl_stats.db` + validate **`both`** parquet and DuckDB before merge.
- [ ] Remove or merge root `pipelines/` into `src/pipelines/`.
- [ ] Tighten lint gate (non-zero pylint floor or Ruff) in backend CI.
- [ ] Align frontend CD docs with reality (Vercel Git integration vs stubbed GitHub Actions deploy block in `ci-frontend.yml`).
- [ ] Optional: projections / ML layer on top of stable weekly exports.

---

## Deploy (where things live today)

- **Backend:** Docker/Render-style deploy hook referenced in `ci-backend.yml` (`RENDER_DEPLOY_HOOK_URL`).
- **Frontend:** Vercel-friendly static build under `frontend/nflstats-pro-ui` (`vercel.json` present); production deploy wiring may be Vercel dashboard or future uncommented workflow—check repo secrets and comments in `ci-frontend.yml`.

---

*Internal use. NFLStatsPro 2026.*
