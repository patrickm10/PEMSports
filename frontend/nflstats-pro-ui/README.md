# NFLStatsPro UI

Vite + React 19 dashboard for NFL fantasy rankings. Consumes the FastAPI backend under `/api/v1`.

---

## Prerequisites

- Node 20 (matches `.github/workflows/ci-frontend.yml`)
- Backend running with a baked `data/nfl_stats.db` (see repo root [README](../../README.md))

---

## Setup

```powershell
cd frontend/nflstats-pro-ui
npm ci
cp .env.example .env.local   # optional; defaults to http://localhost:8000/api/v1
npm run dev
```

Dev server: `http://localhost:5173` (typical Vite default).

---

## Environment

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE` | Full API prefix including `/api/v1`, e.g. `https://nflstats-api.onrender.com/api/v1` |
| `VITE_API_BASE_URL` | Alternative: backend origin only; client appends `/api/v1` |

Production: set via Vercel project environment variables.

---

## Scripts

| Command | Action |
|---------|--------|
| `npm run dev` | Vite dev server |
| `npm run build` | `tsc -b && vite build` |
| `npm run lint` | ESLint |
| `npm run preview` | Preview production build |

---

## API client

Primary client: `src/api/rankingsApi.ts`

- Seasonal rankings: `GET /rankings/{pos}`
- Weekly rankings: `GET /rankings/{pos}/weekly`
- Weekly CSV: `GET /rankings/{pos}/weekly/csv`
- Seasons: `GET /rankings/{pos}/seasons` (returns `number[]`)
- Weeks: `GET /rankings/{pos}/weeks`

See repo root [README](../../README.md) for production URLs and deploy steps.

---

## Deploy

- **Vercel (recommended):** Root Directory = `frontend/nflstats-pro-ui` (or repo root with root `vercel.json`), domain `pemsports.com`, set `VITE_API_BASE`.
- **GitHub Actions:** `.github/workflows/ci-frontend.yml` gates lint + build; Vercel Git integration handles production deploy on `main`.

---

## Structure (high level)

```text
src/
  api/           HTTP clients (rankings, auth, players)
  components/    Grid, charts, v2 landing
  v3/            Player analytics, layout, search
  hooks/         Data fetching (React Query)
  models/        TypeScript ranking types
```

Runtime schema reference: `src/v3/schemas/player.ts` and `src/models/Ranking.ts`.
