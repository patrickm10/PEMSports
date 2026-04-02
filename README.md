# NFLStatsPro: Professional NFL Analytics Platform

**NFLStatsPro** is a high-performance, production-grade analytics platform designed for deep-dive NFL player performance analysis, fantasy football forecasting, and environmental impact assessment.

The system features a robust data pipeline that scrapes raw statistics from industry-standard sources, processes them with high-performance engines, and delivers multi-dimensional rankings via an optimized React frontend.

---

## 🏗️ System Architecture

The platform follows a decoupled, data-centric architecture optimized for analytical performance.

### End-to-End Data Flow
1.  **Ingestion**: Scrapers in `src/pipelines/scrapers/` fetch HTML from FantasyPros and NFL.com.
2.  **Processing**: Orchestrators in `src/pipelines/` clean raw HTML, normalize schemas using Polars, and persist data in Parquet/CSV formats.
3.  **Storage**: Analytical datasets are stored in `data/official_rankings/`, using Parquet for columnar efficiency.
4.  **Query Engine**: A DuckDB-powered engine (`src/backend/data/query_engine.py`) dynamically registers views, performs complex JOINs with environmental metadata, and executes sub-millisecond ranking queries.
5.  **API**: A FastAPI service (`src/backend/api/`) exposes clean REST endpoints, bypassing heavy Pydantic serialization for large analytical payloads.
6.  **Frontend**: A Vite-powered React application (`frontend/nflstats-pro-ui`) provides a premium "Midnight Slate" interface with virtualized tables for high-density data viewing.

---

## 📊 Data Pipeline

### Scraping & Extraction
- **Logic**: Custom BeautifulSoup-based scrapers (`fantasypros.py`) extract data directly from source tables.
- **Dynamic Schema**: The pipeline dynamically identifies headers and row data, ensuring that changing source HTML doesn't break the ingestion flow.
- **Deduplication**: Automatically handles duplicate headers (e.g., 'R_' prefix for rushing yards vs 'P_' for passing).

### Transformations & Rankings
- **Engine**: Powered by Polars for lightning-fast ETL.
- **Storage**: Optimized Parquet and CSV files stored by position and year.
- **Ranking Logic**: DuckDB calculates rankings on-the-fly using `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY fpts_ppr DESC)`.

---

## ⚙️ Backend (FastAPI)

### Setup & Startup
```powershell
$env:PYTHONPATH="src"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Core Endpoints
- **Seasonal Rankings**: `GET /rankings/{pos}?year={year}`
- **Weekly Rankings**: `GET /rankings/{pos}/weekly?year={year}&week={week}`
- **Health Check**: `GET /health` (Verifies presence of all 6 position data files)

### Interaction Parameters
- `pos`: Position code (QB, RB, WR, TE, K, DST).
- `year`: Season year (e.g., 2024).
- `week`: Specific week for weekly view (1-18).

### Known Reliability Fixes
- **Path Resolution**: Paths are resolved relative to `__file__` in the backend, ensuring the server runs correctly from any working directory.
- **Dynamic SQL**: DuckDB views now dynamically inspect source columns to avoid "Binder Error: column not found" when optional enrichment columns are missing.

---

## 💻 Frontend (React)

### Setup & Startup
```powershell
cd frontend/nflstats-pro-ui
npm install
npm run dev
```

### Key Integrations
- **API Client**: `rankingsApi.ts` provides strongly-typed fetchers for seasonal and weekly data.
- **State Management**: Uses React state and effects to trigger re-fetches on filter transitions.
- **Schema Validation**: Warnings are logged on schema drift, but the application continues to render available data to prevent "White Screen of Death" crashes.

### Known UI Solutions
- **Virtualization**: `RankingsTableV2.tsx` uses TanStack Virtual to handle 500+ rows with constant 60FPS scrolling.
- **Dynamic Columns**: Tables automatically adapt column visibility based on the presence of data in the API response.

---

## 🛠️ Local Development & Debugging

### Prerequisites
- Python 3.10+
- Node.js 18.x+
- Windows OS (PowerShell 7 recommended)

### Reproducing Data
1.  **Regenerate Weekly**: `$env:PYTHONPATH="src"; python src/pipelines/get_weekly_rankings.py`
2.  **Regenerate Seasonal**: `$env:PYTHONPATH="src"; python src/pipelines/get_full_season_rankings.py`

### Debugging Guide
| Issue | Root Cause | Fix |
| :--- | :--- | :--- |
| **500 Internal Error on Weekly** | DuckDB EXCLUDE mismatch or duplicate column. | Update `_ensure_weekly_view` to use `source_cols` inspection. |
| **Empty Table (Frontend)** | API param mismatch (`pos` vs `position`). | Ensure `rankingsApi.ts` uses `pos` for all requests. |
| **Data Not Found (Backend)** | Server started from wrong directory. | Ensure path resolution logic uses absolute root detection. |
| **Schema Drift Errors** | New stats added to scraper but not frontend. | Update `validateSchema.ts` to log warnings instead of throwing. |

---

## 📈 Testing & Verification
- **Endpoint Audit**: Run `GET /health` to confirm all 6 position files are detected.
- **E2E Check**: Use the browser developer tools to verify state transitions when switching tabs from QB → RB and Season → Weekly.
- **Boundary Verification**: Ensure a season with only 1 week of data (e.g., 2025) loads correctly in both views.

---

## ✨ Future Improvements
- **Live Scraping**: Real-time stats during game time.
- **Visual Analytics**: Interactive charts for player performance trends.
- **Predictive Modeling**: Integrate an ML layer for week-to-week projections.

---

## 📜 License
Internal use only.
