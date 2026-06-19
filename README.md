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
- **ETL:** Canonical code under **`src/pipelines/`** — operator commands in [`docs/PIPELINE_RUNBOOK.md`](docs/PIPELINE_RUNBOOK.md). Root `pipelines/` is deprecated (redirect README only).

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

Copy `.env.example` to `.env.local` if you need a non-default API base. Ensure **`ALLOWED_ORIGINS`** on the server lists your Vite origin (defaults in `main.py` include `http://localhost:5173`).

### 3. Convenience (Windows)

`scripts/manage_services.py` starts/stops local FastAPI + Vite; it is **Windows-only** as written.

---

## Testing and data checks

Mirror the backend CI gate locally:

```powershell
$env:PYTHONPATH="src"
python scripts/bake_db.py
python scripts/validate_db_completeness.py --mode both
python -m pytest tests/ -v --tb=short
```

**Backend CI** (`.github/workflows/ci-backend.yml`) runs the same sequence: lint → bake → validate **`both`** → pytest. It does **not** commit `data/nfl_stats.db` (gitignored).

**Frontend CI** (`.github/workflows/ci-frontend.yml`) is intended to lint/build the UI under `frontend/nflstats-pro-ui/` — verify workflow paths before relying on it (see Known issues).

---

## Known issues (adversarial review, 2026-06-17)

| Issue | Status |
|--------|--------|
| ~~Health test mismatch~~ | **Fixed** — `/health` returns `positions_available` and `data_files_found` from DuckDB |
| ~~Frontend CI path~~ | **Fixed** — workflow uses `frontend/nflstats-pro-ui/` |
| ~~Deploy without bake~~ | **Fixed** — `render.yaml` and `Dockerfile` run `bake_db.py` at build |
| ~~Weekly CSV route~~ | **Fixed** — `GET /rankings/{pos}/weekly/csv` + frontend client updated |
| ~~Weekly alias routes in UI~~ | **Fixed** — frontend uses canonical `/rankings/{pos}/weekly` |
| **Frontend ESLint gate** | `npm run lint` reports pre-existing errors in v3 components — CI may fail until resolved |

Full findings: [`state_handoff.md`](state_handoff.md).

---

## Limitations

| Topic | Detail |
|--------|--------|
| **`nfl_stats.db`** | Gitignored. Fresh clones have no API database until you run `bake_db.py`. |
| **CI parity** | Backend CI bakes and validates Parquet ↔ DuckDB with `--mode both`. Deploy pipelines must bake separately unless extended. |
| **Postgres** | Optional in development; production/staging expect a real `DATABASE_URL` and strict config. |
| **DuckDB / SQL edge cases** | Historical non-QB weekly paths hit DuckDB optimizer limits when scanning raw parquet through certain window patterns; **bake** + served tables is the supported mitigation (see `bake_db.py` header). |
| **Handoff docs** | `state_handoff.md`, `CHLOG.md`, and `docs/` are gitignored — update locally; they are not on remote by default. |

---

## Roadmap (short)

- [x] CI: bake `nfl_stats.db` + validate **`both`** parquet and DuckDB before merge.
- [x] Fix backend CI blocker: align `/health` contract with tests.
- [x] Fix frontend CI paths (`frontend/nflstats-pro-ui/`).
- [x] Bake DuckDB in Render/Docker deploy build step.
- [x] Align frontend API client with canonical versioned routes (weekly + CSV).
- [ ] Fix frontend ESLint errors blocking CI gate.
- [x] Align frontend CD docs with reality (Vercel Git integration vs stubbed GitHub Actions deploy block in `ci-frontend.yml`).
- [x] Consolidate pipeline roots + publish ETL runbook (`docs/PIPELINE_RUNBOOK.md`).
- [ ] Optional: projections / ML layer on top of stable weekly exports.

---

## Production

| Surface | URL |
|---------|-----|
| Frontend | https://pemsports.com |
| Backend API | https://nflstats-api.onrender.com |
| Health | https://nflstats-api.onrender.com/health |
| API docs | https://nflstats-api.onrender.com/docs |

**Environment wiring**

| Platform | Variable | Value |
|----------|----------|-------|
| Vercel (frontend) | `VITE_API_BASE` | `https://nflstats-api.onrender.com/api/v1` |
| Render (backend) | `ALLOWED_ORIGINS` | `https://pemsports.com,https://www.pemsports.com` |
| Render (backend) | `DATABASE_URL` | Auto-linked from `nflstats-db` via [`render.yaml`](render.yaml) |
| GitHub (backend CD) | `RENDER_DEPLOY_HOOK_URL` | Deploy hook from Render service settings |

**Verify after deploy**

```powershell
.\scripts\verify_production.ps1
```

---

## Deploy

### Backend (Render)

Blueprint: [`render.yaml`](render.yaml) — Python web service `nflstats-api`, Render Postgres `nflstats-db`, bake step in `buildCommand`, health check on `/health`, `autoDeploy: true`.

1. Render Dashboard → **New Blueprint** → connect this GitHub repo.
2. After first deploy, copy the deploy hook URL into GitHub secret `RENDER_DEPLOY_HOOK_URL` (optional; blueprint `autoDeploy` also redeploys on push to `main`).
3. Backend CI (`.github/workflows/ci-backend.yml`) runs lint → bake → validate → pytest, then curls the deploy hook on `main` when the secret is set.

### Frontend (Vercel + pemsports.com)

Public UI is the Vite SPA under **`frontend/nflstats-pro-ui`**. Do **not** deploy the repo root as a serverless FastAPI app (`api/index.py` is legacy only).

**Recommended:** Vercel project → Root Directory = `frontend/nflstats-pro-ui`, Production branch = `main`, domain `pemsports.com`. Set `VITE_API_BASE` in Vercel env (also committed in [`frontend/nflstats-pro-ui/vercel.json`](frontend/nflstats-pro-ui/vercel.json) and root [`vercel.json`](vercel.json) for repo-root-linked projects).

**CD:** Vercel Git integration redeploys on push to `main` when frontend paths change. Frontend CI (`.github/workflows/ci-frontend.yml`) gates lint + build on every PR/push.

### Docker (optional)

[`Dockerfile`](Dockerfile) at repo root runs `bake_db.py` at build and serves via gunicorn — useful for local/container parity, not the primary production path.

---

*Internal use. NFLStatsPro 2026.*
