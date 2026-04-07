# 🏈 NFLStatsPro: Weekly Alpha Predictive Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://reactjs.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1%2B-orange.svg)](https://xgboost.ai/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.3%2B-yellow.svg)](https://duckdb.org/)

**NFLStatsPro** is a production-grade predictive analytics platform. It features the **"Weekly Alpha"** engine—an XGBoost-powered ML model that predicts situational performance "Deltas" (deviations from baseline) by analyzing environmental and momentum features.

---

## 🏛️ Project Architecture

The system uses a decoupled **Strategy B** data model with high-performance Parquet storage and a multi-stage containerization strategy.

### 📂 Repository Organization
```text
NFLStatsAnalyzer/
├── data/                 # 🟢 Optimized Parquet Store
│   ├── rankings/         # Consolidated historical positional datasets
│   └── forecasts/        # 🔮 ML Alpha Forecasts (Smart Projections)
├── docker-compose.yml    # 🐳 Production Orchestration (API + DB)
├── src/                  # 🛠️ System Core
│   ├── backend/          # FastAPI Engine (CORS & HTTPS Hardened)
│   │   ├── api/          # Predictive & Impact routes
│   │   ├── data/         # Portable Repository Pattern (Postgres + local)
│   │   └── models/       # Pydantic 2.0 Data Models
│   └── pipelines/        # 🧠 ML Feature Store & XGBoost Orchestrator
└── frontend/             # Midnight Slate Dashboard (React + Framer Motion)
```

---

## ⚡ Technical Stack

-   **Predictive Modeling**: [XGBoost](https://xgboost.ai/) Regressors with [SHAP](https://shap.readthedocs.io/) for explainable AI insights.
-   **Storage Engine**: [DuckDB](https://duckdb.org/) for joining historical stats with ML forecasts in sub-milliseconds.
-   **ETL & Features**: [Polars](https://www.pola.rs/) for 3-game rolling momentum and situational feature engineering.
-   **Infrastructure**: [Docker](https://www.docker.com/) multi-stage builds with [PostgreSQL](https://www.postgresql.org/) for persistent CRUD insights.
-   **UI/UX**: [React 19](https://reactjs.org/) + [Framer Motion](https://www.framer.com/motion/) for premium "Pro Insights" visualizations.

---

## 🚀 Getting Started

### 🐳 Docker Deployment (Recommended)
Launch the entire platform including the hardened API and Postgres database:
```powershell
# Requires Docker Desktop
docker compose up --build -d
```

### 🧠 ML Pipeline Execution
Generate the latest Alpha Forecasts from the Strategy B Parquet store:
```powershell
$env:PYTHONPATH="src"
python src/pipelines/ml_orchestrator.py
```

---

## 📈 Analytical Endpoints

-   **Alpha Forecasts**: `GET /api/v1/rankings/{pos}/weekly?year=2024&week=13`
    *   Returns `smart_projection`, `predicted_alpha`, and `insight_flags`.
-   **Pro Insights**: Explainable AI view via the **ProInsightsDrawer** UI.
-   **Health Audit**: `GET /health` (Verifies Strategy B & Forecasting assets).

---

## 📜 Roadmap
- [x] **Strategy B Refactor**: Position-centric Parquet consolidation.
- [x] **Weekly Alpha Engine**: XGBoost + SHAP predictive layer.
- [x] **Containerization**: Hardened Docker + Postgres infrastructure.
- [/] **2025 Seasonal Hardening**: Aggregating weekly totals into seasonal stats.
- [ ] **Vegas Automation**: Real-time Betting API integration (Spread/OU).
- [ ] **Situational Notes**: Persistent user-saved situational CRUD.

---
*Internal use only. NFLStatsPro 2026. Data Audit Verified: Apr 6 2026.*
