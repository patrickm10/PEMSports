# PEM Sports Website

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
frontend/nflstats-pro-ui  (Vite, React 19)  →  https://pemsports.com
```

- **Rankings data:** Parquet on disk → materialized tables in `nfl_stats.db` for stable SQL and low cold-start cost on Render.
- **Transactional / auth:** PostgreSQL via `psycopg` (`src/backend/data/postgres.py`). In **development**, a missing DB logs a warning and auth features degrade; **staging/production** fail startup if the pool cannot open (`src/backend/core/config.py` policy).
- **ETL:** Canonical code under **`src/pipelines/`** — operator commands in [`docs/PIPELINE_RUNBOOK.md`](docs/PIPELINE_RUNBOOK.md). Root `pipelines/` is deprecated (redirect README only).

---

## Production (target)

| Surface | URL | Status (2026-06-19) |
|---------|-----|---------------------|
| Frontend | https://pemsports.com | **Not live** — 500 until Vercel redeploys SPA (exclude legacy `api/`) |
| Backend API | https://nflstats-api.onrender.com | **Not live** — apply Render Blueprint from `render.yaml` |
| Health | https://nflstats-api.onrender.com/health | Pending backend deploy |
| API docs | https://nflstats-api.onrender.com/docs | Pending backend deploy |

**Environment wiring**

| Platform | Variable | Value |
|----------|----------|-------|
| Vercel (frontend) | `VITE_API_BASE` | `https://nflstats-api.onrender.com/api/v1` |
| Render (backend) | `ALLOWED_ORIGINS` | `https://pemsports.com,https://www.pemsports.com` |
| Render (backend) | `DATABASE_URL` | Auto-linked from `nflstats-db` via [`render.yaml`](render.yaml) |
| GitHub (backend CD) | `RENDER_DEPLOY_HOOK_URL` | Deploy hook from Render service settings (optional) |

**Verify when live**

```powershell
.\scripts\verify_production.ps1
```

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

Run API:

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

### 3. Convenience (Windows)

`scripts/manage_services.py` starts/stops local FastAPI + Vite; **Windows-only**.

---

## Testing and data checks

```powershell
$env:PYTHONPATH="src"
python scripts/bake_db.py
python scripts/validate_db_completeness.py --mode both
python -m pytest tests/ -v --tb=short
```

**Backend CI** (`.github/workflows/ci-backend.yml`): lint → bake → validate **`both`** → pytest → Render deploy hook (if secret set).

**Frontend CI** (`.github/workflows/ci-frontend.yml`): eslint → vite build in `frontend/nflstats-pro-ui/`.

---

## Deploy

### Backend (Render) — primary API host

[`render.yaml`](render.yaml): web service `nflstats-api`, Postgres `nflstats-db`, `buildCommand` includes `bake_db.py`, health check `/health`, `autoDeploy: true`.

Do **not** use root [`api/index.py`](api/index.py) for production — no bake step, read-only FS constraints, requires Postgres at cold start.

### Frontend (Vercel + pemsports.com)

Public UI: Vite SPA under **`frontend/nflstats-pro-ui`**.

- Root-linked projects: [`vercel.json`](vercel.json) + [`.vercelignore`](.vercelignore) (excludes `api/`) + root [`package.json`](package.json) build script.
- Subdir-linked projects: set Root Directory to `frontend/nflstats-pro-ui` and use [`frontend/nflstats-pro-ui/vercel.json`](frontend/nflstats-pro-ui/vercel.json).

**CD:** Vercel Git integration redeploys on push to `main`. Frontend CI gates PRs.

---

## Known issues

| Issue | Status |
|--------|--------|
| Production not live | **In progress** — Render Blueprint + Vercel SPA redeploy required |
| Legacy root `api/` on Vercel | **Mitigated** — `.vercelignore` excludes serverless path |
| Ranking column contract | **Open** — Roadmap Task 3 (after live) |
| Handoff / docs local only | `state_handoff.md`, `docs/` gitignored — update locally |

Full operator state: [`state_handoff.md`](state_handoff.md).

---

## Limitations

| Topic | Detail |
|--------|--------|
| **Render cold start** | First request after idle may take 30–60s on starter tier. |

---

## Roadmap (short)

- [ ] Ranking column contract (Task 3).
- [ ] Optional: projections / ML layer.

---

*Internal use. NFLStatsPro 2026.*
