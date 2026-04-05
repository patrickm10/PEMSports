# 🏈 NFLStatsPro: Professional Analytics Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Latest-yellow.svg)](https://duckdb.org/)
[![Polars](https://img.shields.io/badge/Polars-Latest-orange.svg)](https://www.pola.rs/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)

**NFLStatsPro** is a high-performance, production-grade analytics platform designed for deep-dive NFL player performance analysis, fantasy football forecasting, and environmental impact assessment. 

The system features a **strictly standardized data architecture** optimized for sub-millisecond analytical queries and lean GitHub repository management.

---

## 🏛️ Project Architecture

The platform follows a decoupled, data-centric architecture using a "Small Index, Big Data" strategy for Git management.

### 📂 Repository Organization
```text
NFLStatsAnalyzer/
<<<<<<< HEAD
├── data/                 # 🟢 GIT-TRACKED (Optimized Parquet)
│   └── rankings/         # Position-centric consolidated Parquet files
├── data_local/           # 🔴 LOCAL-ONLY (Raw CSV Scrapes - .gitignored)
│   └── raw_scrapes/      # Source HTML/CSV outputs from pipelines
├── frontend/             # Midnight Slate UI (Vite + React)
│   └── nflstats-pro-ui/  # Main dashboard application
├── src/
│   ├── backend/          # FastAPI REST API & Analytical Engines
│   │   ├── api/          # Route handlers & Auth
│   │   └── data/         # DuckDB & Postgres implementations
│   └── pipelines/        # Scrapers & Polars ETL
└── tests/                # Comprehensive Pytest suite
=======
├── backend/
│   ├── api/
│   |    ├── routes.py/                   # Routing for dataframes
│   ├── services/                         # Code for cleaning and loading data
│   |    ├── k_service.py/
│   |    ├── qb_service.py/
│   |    ├── rb_service.py/
│   |    ├── te_service.py/
│   |    ├── wr_service.py/
│   ├── utils/
│   |    ├── file_loader.py/      
│   ├── main.py                           # Main entry point for FastAPI
├── data/
│   ├── qb_weekly_stats/
│   ├── rb_weekly_stats/
│   ├── wr_weekly_stats/
│   ├── te_weekly_stats/
│   ├── official_stats/
│   |   ├── official_qb_stats.csv/
│   |   ├── official_rb_stats.csv/
│   |   ├── official_te_stats.csv/
│   |   ├── official_wr_stats.csv/
│   |   ├── official_k_stats.csv/
│   ├── nfl_metadata/
├── pipelines/
│   ├── get_nfl_schedule.py
│   ├── get_weekly_stats.py
│   ├── get_offensive_rankings.py
│   ├── get_defensive_rankings.py
├── frontend/
│   ├── src/
│   |    ├── App.jsx
│   |    ├── App.css
│   ├── public/
│   |    ├── package.json
├── season_scripts/
│   ├── get_adp_stats.py
│   ├── get_career_stats.py
│   ├── get_roster_per_team.py
├── analytics/
│   ├── chatbot.py
│   ├── draft_calculator.py
│   ├── nlp_model.py (in progress)
├── README.md
├── requirements.txt
>>>>>>> c1f405538b6e91996c9e4435cfc5b8da10fc6803
```

---

## ⚡ Core Technical Stack

-   **Query Engine**: [DuckDB](https://duckdb.org/) for in-memory analytical processing.
-   **ETL Pipeline**: [Polars](https://www.pola.rs/) for lightning-fast data transformation.
-   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) with JWT-based OAuth2 authentication.
-   **Frontend**: [React 18](https://reactjs.org/) + Vite with TanStack Virtual for high-performance data rendering.
-   **Database**: **PostgreSQL** for user sessions and state management (with graceful local fallback).

---

## 📅 Data Strategy & Reproducibility

### Strict Separation of Concerns
To maintain a clean GitHub footprint while preserving raw history, we split storage:
1.  **Tracked Parquet (`data/rankings/`)**: Only optimized, consolidated Parquet files are committed to Git. This provides 10x better compression than CSV and native DuckDB speed.
2.  **Ignored Raw Data (`data_local/`)**: All individual week/position CSV scrapes are kept locally for reproducibility but excluded from Git to prevent repository bloat.

### Reproducing Data
The pipelines are idempotent and designed for incremental growth.
```powershell
# Standardize Weekly Rankings (2020-2025)
$env:PYTHONPATH="src"
python src/pipelines/get_weekly_rankings.py

# Standardize Seasonal Totals
$env:PYTHONPATH="src"
python src/pipelines/get_full_season_rankings.py
```

---

## 🚀 Getting Started

### Backend Setup
1. **Environment**: Python 3.10+
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Configure Settings**: `cp .env.example .env` (Add `DATABASE_URL` and `JWT_SECRET`)
4. **Launch Server**: `uvicorn src.backend.main:app --reload`

### Frontend Setup
1. **Environment**: Node.js 18+
2. **Setup**: `cd frontend/nflstats-pro-ui && npm install`
3. **Run**: `npm run dev`

---

## 📈 Analytical Endpoints

-   **Health Audit**: `GET /health` (Verifies presence of all core positional assets)
-   **Seasonal Rankings**: `GET /api/v1/rankings/{pos}?year={year}`
-   **Weekly Rankings**: `GET /api/v1/rankings/{pos}/weekly?year={year}&week={week}`
-   **Impact Splits**: `GET /api/v1/rankings/{pos}/impact/{player_id}?metric_type=surface`

---

## 🛠️ Testing & Verification

Comprehensive testing is implemented via `pytest`. All query resolution and auth flows are validated before deployment.

```powershell
$env:PYTHONPATH="src"
pytest tests/test_query_engine.py  # Validates DuckDB resolution & Parquet integrity
pytest tests/test_auth_routes.py   # Validates JWT & Postgres flows
```

---

## 📜 Roadmap
- [x] **Strategy B Refactor**: Position-centric Parquet consolidation.
- [x] **Strict Cleanup**: Git index sanitization for all legacy CSVs.
- [ ] **Predictive Modeling**: Integrating ML-based projection layers.
- [ ] **CI/CD Deployment**: Automated Parquet validation on GitHub Actions.

---
*Internal use only. NFLStatsPro 2026.*

