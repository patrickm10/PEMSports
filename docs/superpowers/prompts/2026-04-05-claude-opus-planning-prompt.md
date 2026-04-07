# 🚀 Claude Planning Mode: NFLStatsPro "Weekly Alpha" Deployment

**Objective**: Finalize the containerized deployment and production-grade orchestration of the NFLStatsPro predictive analytics platform.

---

## 🏗️ System Architecture Snapshot
- **Backend**: FastAPI (Python 3.11) with a **Portable Repository Pattern** (PostgreSQL production / JSON local).
- **Analytics**: **Strategy B** Data Model (Consolidated Parquet files) queried via **DuckDB**. 
- **ML Engine**: **XGBoost** regressor predicting situational performance "Deltas" enriched with **SHAP-based explainability**.
- **Frontend**: React 19 + Framer Motion (Midnight Slate UI).
- **Infra**: Multi-stage **Dockerfile** + **Docker Compose** (FastAPI + Postgres 15-Alpine).

## 🛠️ Current Implementation State
1.  **Hardened Files Exist**:
    *   `Dockerfile`: Multi-stage build (Python 3.11-slim) with volume mounts for `/app/data` (DuckDB Parquet assets).
    *   `docker-compose.yml`: Orchestrates `api` and `db` (Postgres) services with shared volumes.
    *   `src/backend/main.py`: CORS and HTTPS hardening implemented via environment variables.
2.  **ML Pipelines**: 
    *   `ml_features.py`: Polars-based feature engineering (Rolling momentum, Vegas placeholders).
    *   `ml_orchestrator.py`: XGBoost training and SHAP forecasting.
3.  **Frontend**:
    *   `ProInsightsDrawer.tsx`: UI for SHAP explainability.
    *   `RankingsTableV2.tsx`: Columnar delta visualization (Arrows/Stripes).

## 🎯 Target Goal
Your task is to act as a **Senior DevOps Engineer** and lead the **Planning & Execution** of the final deployment. You must:
1.  **Audit the Docker Infrastructure**: Verify the `Dockerfile` and `docker-compose.yml` for optimal volume management (DuckDB Parquet files must persist across restarts).
2.  **Verify Repository Portability**: Ensure the `PostgresInsightRepository` correctly handles the connection to the `db` service defined in Docker Compose.
3.  **Environment Orchestration**: Define a robust `.env` strategy for production variables (`ALLOWED_ORIGINS`, `DATABASE_URL`, `JWT_SECRET`).
4.  **Health Integrity Execution**: Utilize the specialized `/health` endpoint (updated for Strategy B) to verify successful data mounting in the container.

## 📜 Technical Constraint Checklist
- **Volume Mounts**: Historical rankings Parquet data resides in `./data/rankings/`. ML forecasts in `./data/forecasts/`. 
- **Cores/Memory**: The Python 3.11-slim image must have adequate resources for DuckDB analytical joins.
- **Portability**: All paths must remain relative to the project root for container portability.
- **Explainability**: SHAP insights are delivered as `string_split` lists from DuckDB.

---

**Instruction for Claude**: "Enter Planning Mode. Analyze the provided repository context. Propose a step-by-step execution plan to launch the NFLStatsPro stack using Docker Compose, focus on resolving path-mapping issues and verifying database connectivity once the container is live."
